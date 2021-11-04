from typing import *
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import auc
from matplotlib import pyplot as plt


# draw PR-diagram and calculate AUC
# https://machinelearningmastery.com/roc-curves-and-precision-recall-curves-for-classification-in-python/
def make_prc_plot(probabilities: List[float], actual_labels: List[int], label: str):
    precision, recall, _ = precision_recall_curve(actual_labels, probabilities)
    auc_value = auc(recall, precision)
    no_skill = sum(actual_labels) / len(actual_labels)  # = P / total
    plt.plot([0, 1], [no_skill, no_skill], linestyle='--', label='No Skill: ' + str(no_skill))
    plt.plot(recall, precision, marker='.', label=label)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    plt.ylim([no_skill - 0.03, 1.03])
    plt.text(0.5, 0.3, f"AUC: {int(auc_value * 1000)/10}%", horizontalalignment='center', verticalalignment='center', transform=plt.gca().transAxes)
    plt.show()


if __name__ == "__main__":
    # generate 2 class dataset
    X, y = make_classification(n_samples=1000000, n_classes=2, random_state=1, weights=(0.9,))
    # split into train/test sets
    trainX, testX, trainy, testy = train_test_split(X, y, test_size=0.5, random_state=2)
    # fit a model
    model = LogisticRegression(solver='lbfgs')
    model.fit(trainX, trainy)
    # predict probabilities
    lr_probs = model.predict_proba(testX)
    # keep probabilities for the positive outcome only
    lr_probs = lr_probs[:, 1]
    make_prc_plot([p for p in lr_probs], [c for c in testy], "Example Curve")
