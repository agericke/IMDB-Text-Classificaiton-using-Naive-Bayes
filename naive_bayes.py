from collections import Counter
from math import log, exp
import re
import os
import sys
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs

# Keep this as a package global variable
ALPHA = 30.0
# End TODO

class IMDBText:
    """Class to represent text, exposing generator function for words
    """
    def __init__(self, idnum, text):
        self.text = text
        self.idnum = idnum

    def get_words(self):
        # Preprocess text
        cleaned = bs(self.text, features="html.parser").text
        for word in cleaned.strip().split():
            word = re.sub(r"^\W+", "", word)
            word = re.sub(r"\W+$", "", word)
            if word:
                yield word


class IMDBReader:
    """Utility class for reading IMDB data
    """
    def __init__(self, data_dir):
        self.data_dir = data_dir
        dir_contents = os.listdir(data_dir)
        assert "pos" in dir_contents and "neg" in dir_contents, \
            "Could not find IMDB data in {}".format(data_dir)


    def get_texts(self, subset):
        """Generator function over texts in subset ('pos' or 'neg') of data
        """
        assert subset in ["pos", "neg"], \
            "Only data subsets 'pos' or 'neg' may be selected"
        for textfile in os.listdir(os.path.join(self.data_dir, subset)):
            if textfile[-4:] == ".txt":
                with open(os.path.join(self.data_dir, subset, textfile),
                          encoding="utf-8") as f:
                    yield IMDBText(textfile[:-4], f.read())


class NaiveBayes:
    """Naive Bayes text categorization model
    """

    def __init__(self, data):
        self.train(data)

    def train(self, data):
        """Train model by collecting counts from training corpus
        """

        # Counts of words in positive-/negative-class texts
        # w_count[w][y=pos]
        self.count_positive = Counter()
        # w_count[w][y=neg]
        self.count_negative = Counter()

        # Total number of reviews for each category
        # d_count[y=pos]
        self.num_positive_reviews = 0
        # d_count[y=neg]
        self.num_negative_reviews = 0

        # Total number of words in positive/negative reviews
        # w_count[y=pos]
        self.total_positive_words = 0
        # w_count[y=neg]
        self.total_negative_words = 0

        # Class priors (logprobs)
        # log(P(y=pos))
        self.p_positive = 0.0
        # log(P(y=neg))
        self.p_negative = 0.0

        for i, text in enumerate(data.get_texts("pos")):
            #
            self.num_positive_reviews += 1;
            for i, word in enumerate(text.get_words()):
                self.count_positive.update([word]);
            #
            if i % 100 == 0:
                sys.stdout.write(".")

        self.total_positive_words = sum(self.count_positive.values());
        print();

        for i, text in enumerate(data.get_texts("neg")):
            #
            self.num_negative_reviews += 1;
            for i, word in enumerate(text.get_words()):
                self.count_negative.update([word]);
            #
            if i % 100 == 0:
                sys.stdout.write(".");
        
        self.total_negative_words = sum(self.count_negative.values());
        print()

        # Calculate derived statistics
        self.vocab = set(list(self.count_negative.keys())
                         + list(self.count_positive.keys()))
        self.p_positive = log(float(self.num_positive_reviews)) \
            - log(float(self.num_positive_reviews + self.num_negative_reviews))
        self.p_negative = log(float(self.num_negative_reviews)) \
            - log(float(self.num_positive_reviews + self.num_negative_reviews))


    def predict(self, data, alpha=1.0):
        """For each text
           - append the text id (file basename) to `text_ids`
           - append the predicted label (1.0 or -1.0) to `pred_labels`
           - append the correct (gold) label (1.0 or -1.0) to `gold_labels`
           - append the probability of the positive (1.0) class to `pred_probs`
        """
        text_ids = []
        pred_labels = []
        pred_probs = []
        gold_labels = []

        for classval in ["pos", "neg"]:
            for text in data.get_texts(classval):
                text_ids.append(text.idnum)
                if classval == "pos":
                    gold_labels.append(1.0)
                else:
                    gold_labels.append(-1.0)
                if len(text_ids) % 100 == 0:
                    sys.stdout.write(".")

                #words = [];
                sum_positive = 0;
                sum_negative = 0;
                for word in text.get_words():
                    # if word not in words:
                        # words.append(word);
                        # log(P(Pos|X))
                        sum_positive += log(self.count_positive[word] + alpha) - log(self.total_positive_words+alpha*len(self.vocab));
                        # log(P(Neg|X))
                        sum_negative += log(self.count_negative[word] + alpha) - log(self.total_negative_words+alpha*len(self.vocab));

                sum_positive += self.p_positive;
                sum_negative += self.p_negative;
                # End TODO

                # Get P(Y|X) by normalizing across log(P(Y,X)) for both values of Y
                # 1) Get K = log(P(Pos|X) + P(Neg|X))
                normalization_factor = self.log_sum(sum_positive, sum_negative)
                # 2) Calculate P(Pos|X) = e^(log(P(Pos,X)) - K)
                predicted_prob_positive = exp(sum_positive - normalization_factor)
                # 3) Get P(Neg|X) = P(Neg|X) = e^(log(P(Neg,X)) - K)
                predicted_prob_negative = 1.0 - predicted_prob_positive

                pred_probs.append(predicted_prob_positive)
                if predicted_prob_positive > predicted_prob_negative:
                    pred_labels.append(1.0)
                else:
                    pred_labels.append(-1.0)
            print()

        return text_ids, gold_labels, pred_labels, pred_probs

    def log_sum(self, logx, logy):
        """Utility function to compute $log(exp(logx) + exp(logy))$
        while avoiding numerical issues
        """
        m = max(logx, logy)
        return m + log(exp(logx - m) + exp(logy - m))


if __name__ == "__main__":
    TRAIN_DATA_DIR = "hw3_data/train"
    TEST_DATA_DIR = "hw3_data/test"

    print("Computing parameters")
    NB = NaiveBayes(IMDBReader(TRAIN_DATA_DIR))

    print("Predicting on test set")
    TEST_IDS, GOLD_LABELS, PRED_LABELS, PRED_PROBS = NB.predict(IMDBReader(TEST_DATA_DIR), alpha=ALPHA)

    print("Evaluating")
    ACCURACY = np.sum(np.equal(PRED_LABELS, GOLD_LABELS)) / float(len(GOLD_LABELS))
    print("Test accuracy: {:.2f}%".format(100 * ACCURACY))

    outfile = "predictions.csv"
    print("Printing test set predictions to {}".format(outfile))
    pd.DataFrame({"File ID": TEST_IDS,
                  "Class": GOLD_LABELS,
                  "Predicted Class": PRED_LABELS,
                  "Predicted Probability": PRED_PROBS}).to_csv(outfile)