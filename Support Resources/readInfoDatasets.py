import pickle
import numpy as np


documents = pickle.load(open("FakeNewsNet/dict_documents.pkl", "rb"))
indexes = np.load('FakeNewsNet/indexes.npy')
labels = np.load('FakeNewsNet/labels.npy')

for i in range(len(indexes)):
    index = indexes[i]
    label = labels[i]
    txt = documents[index]
