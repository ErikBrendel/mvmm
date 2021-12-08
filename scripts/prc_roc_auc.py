from typing import *
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.metrics import auc
from matplotlib import pyplot as plt


PRC_PLOT_DATA_ENTRY = Tuple[str, Union[List[float], List[int]]]


# draw PR-diagram and calculate AUC
# https://machinelearningmastery.com/roc-curves-and-precision-recall-curves-for-classification-in-python/
def make_prc_plot(data_list: List[PRC_PLOT_DATA_ENTRY], actual_labels: List[int], title: str, show=True):

    no_skill_precision = sum(actual_labels) / len(actual_labels)  # = P / total
    plt.plot([0, 1], [no_skill_precision, no_skill_precision], linestyle='--', color="gray", label=f'No Skill: {int(no_skill_precision * 1000) / 10}%')

    for datum_name, datum_prediction in data_list:
        if any(isinstance(v, float) for v in datum_prediction):  # list of probability assignments and true labels
            precision, recall, _ = precision_recall_curve(actual_labels, datum_prediction)
            if len(precision) > 3:
                precision = precision[:-1]
                recall = recall[:-1]
            auc_value = auc(recall, precision)
            plot_kwargs = {"marker": ",", "alpha": 0.8}
        else:  # list of binary classes
            tp = sum(a == 1 and p == 1 for a, p in zip(actual_labels, datum_prediction))
            if tp == 0:
                precision = 0
                recall = 0
            else:
                fp = sum(a == 0 and p == 1 for a, p in zip(actual_labels, datum_prediction))
                fn = sum(a == 1 and p == 0 for a, p in zip(actual_labels, datum_prediction))
                precision = tp / float(tp + fp)
                recall = tp / float(tp + fn)
            # going horizontally left from any valid point is always possible by just taking a smaller sample of the result set
            # this keeps precision constant (expectedly), and reduces recall
            # the auc is thus all the area lower-left of both valid points: the one given, and the return-all-point
            auc_value = precision * recall + no_skill_precision * (1 - recall)
            plot_kwargs = {"marker": "X", "linestyle": "None", "color": "k"}
        plt.plot(recall, precision, label=f"{datum_name}: {int(auc_value * 1000)/10}%", **plot_kwargs)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    # plt.ylim([no_skill_precision - 0.03, 1.03])
    plt.ylim([-0.03, 1.03])
    plt.title(title)
    if show:
        plt.show()


# https://scikit-learn.org/stable/auto_examples/model_selection/plot_roc.html#sphx-glr-auto-examples-model-selection-plot-roc-py
def make_roc_plot(data_list: List[PRC_PLOT_DATA_ENTRY], actual_labels: List[int], title: str, show=True):

    plt.plot([0, 1], [0, 1], linestyle='--', label=f'No Skill: 50%')

    for datum_name, datum_prediction in data_list:
        if any(isinstance(v, float) for v in datum_prediction):  # list of probability assignments and true labels
            fpr, tpr, _ = roc_curve(actual_labels, datum_prediction)
            auc_value = auc(fpr, tpr)
            marker = "."
        else:  # list of binary classes
            tp = sum(a == 1 and p == 1 for a, p in zip(actual_labels, datum_prediction))
            fp = sum(a == 0 and p == 1 for a, p in zip(actual_labels, datum_prediction))
            p = sum(label == 1 for label in actual_labels)
            n = len(actual_labels) - p
            fpr = fp / float(n)
            tpr = tp / float(p)
            auc_value = tpr * (1 - fpr)
            marker = "x"
        plt.plot(fpr, tpr, marker=marker, label=f"{datum_name}: {int(auc_value * 1000)/10}%")
    plt.xlim([-0.03, 1.03])
    plt.ylim([-0.03, 1.03])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.title(title)
    if show:
        plt.show()


if __name__ == "__main__":
    # generate 2 class dataset
    X, y = make_classification(n_samples=100000, n_classes=2, random_state=1, weights=(0.9,))
    # split into train/test sets
    trainX, testX, trainy, testy = train_test_split(X, y, test_size=0.5, random_state=2)
    # fit a model
    model = LogisticRegression(solver='lbfgs')
    model.fit(trainX, trainy)
    # predict probabilities
    lr_probs = model.predict_proba(testX)
    # keep probabilities for the positive outcome only
    lr_probs = lr_probs[:, 1]
    make_prc_plot([
        ("Example Curve", [p for p in lr_probs]),
    ], [c for c in testy], "PRC example")
    make_roc_plot([
        ("Example Curve", [p for p in lr_probs]),
    ], [c for c in testy], "ROC example")
