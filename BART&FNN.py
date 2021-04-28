# %%
import datetime
import os
import sys
import io
from sklearn.model_selection import train_test_split
from distutils.version import LooseVersion as LV
from transformers import AdamW, get_linear_schedule_with_warmup
from transformers import BertForSequenceClassification
from transformers import BertTokenizer, BertConfig
from torch.utils.data import (TensorDataset, DataLoader,
                              RandomSampler, SequentialSampler)
import torch
import numpy as np
import pickle
from IPython import get_ipython

# %% [markdown]
# <a href="https://colab.research.google.com/github/GabrielBG0/Fakenews-Recognition/blob/main/Bart_%26_FNN_2.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# %%
# Deleting default sample data folder
get_ipython().system('rm -rf /content/sample_data')
get_ipython().system('unzip FakeNewsNet.zip')


# %%
# Install aditional librarys
get_ipython().system('pip install transformers')
get_ipython().system('pip install datasets')


# %%


documents = pickle.load(open("FakeNewsNet/dict_documents.pkl", "rb"))
indexes = np.load('FakeNewsNet/indexes.npy')
lbls = np.load('FakeNewsNet/labels.npy')

texts = []
labels = []
for i in range(len(indexes)):
    index = indexes[i]
    texts.append(documents[index])
    if lbls[i] == np.str_("-1"):
        labels.append(0)
    else:
        labels.append(1)

print("lable 1: " + str(labels[0]))
print("text 1: " + texts[0])
print(type(labels[0]))


# %%
for text in texts:
    if len(text.split(' ')) > 512:
        print("there are too long texts! truncate then")
        break


# %%


# %%
if 'DATADIR' in os.environ:
    DATADIR = os.environ['DATADIR']
else:
    DATADIR = "/content/"


# %%
# Split the data into a training set and a test set using
# scikit-learn's train_test_split().

TEST_SET = 4000

(sentences_train, sentences_test,
 labels_train, labels_test) = train_test_split(texts, labels,
                                               test_size=TEST_SET,
                                               shuffle=True, random_state=42)

print('Length of training texts:', len(sentences_train))
print('Length of training labels:', len(labels_train))
print('Length of test texts:', len(sentences_test))
print('Length of test labels:', len(labels_test))


# %%
# The token [CLS] is a special token required by BERT at the beginning
# of the sentence.

sentences_train = ["[CLS] " + s for s in sentences_train]
sentences_test = ["[CLS] " + s for s in sentences_test]

print("The first training sentence:")
print(sentences_train[0], 'LABEL:', labels_train[0])


# %%
# Next we specify the pre-trained BERT model we are going to use. The
# model `"bert-base-uncased"` is the lowercased "base" model
# (12-layer, 768-hidden, 12-heads, 110M parameters).
#
# We load the used vocabulary from the BERT model, and use the BERT
# tokenizer to convert the sentences into tokens that match the data
# the BERT model was trained on.

print('Initializing BertTokenizer')

BERTMODEL = 'bert-base-uncased'
CACHE_DIR = os.path.join(DATADIR, 'transformers-cache')

tokenizer = BertTokenizer.from_pretrained(BERTMODEL, cache_dir=CACHE_DIR,
                                          do_lower_case=True)

tokenized_train = [tokenizer.tokenize(s) for s in sentences_train]
tokenized_test = [tokenizer.tokenize(s) for s in sentences_test]

print("The full tokenized first training sentence:")
print(tokenized_train[0])


# %%
# Now we set the maximum sequence lengths for our training and test
# sentences as `MAX_LEN_TRAIN` and `MAX_LEN_TEST`. The maximum length
# supported by the used BERT model is 512.
#
# The token `[SEP]` is another special token required by BERT at the
# end of the sentence.

MAX_LEN_TRAIN, MAX_LEN_TEST = 128, 512

tokenized_train = [t[:(MAX_LEN_TRAIN-1)]+['SEP'] for t in tokenized_train]
tokenized_test = [t[:(MAX_LEN_TEST-1)]+['SEP'] for t in tokenized_test]

print("The truncated tokenized first training sentence:")
print(tokenized_train[0])


# %%
# Next we use the BERT tokenizer to convert each token into an integer
# index in the BERT vocabulary. We also pad any shorter sequences to
# `MAX_LEN_TRAIN` or `MAX_LEN_TEST` indices with trailing zeros.

ids_train = [tokenizer.convert_tokens_to_ids(t) for t in tokenized_train]
ids_train = np.array([np.pad(i, (0, MAX_LEN_TRAIN-len(i)),
                             mode='constant') for i in ids_train])

ids_test = [tokenizer.convert_tokens_to_ids(t) for t in tokenized_test]
ids_test = np.array([np.pad(i, (0, MAX_LEN_TEST-len(i)),
                            mode='constant') for i in ids_test])

print("The indices of the first training sentence:")
print(ids_train[0])


# %%
# BERT also requires *attention masks*, with 1 for each real token in
# the sequences and 0 for the padding:

amasks_train, amasks_test = [], []

for seq in ids_train:
    seq_mask = [float(i > 0) for i in seq]
    amasks_train.append(seq_mask)

for seq in ids_test:
    seq_mask = [float(i > 0) for i in seq]
    amasks_test.append(seq_mask)


# %%
# We use again scikit-learn's train_test_split to use 10% of our
# training data as a validation set, and then convert all data into
# torch.tensors.

(train_inputs, validation_inputs,
 train_labels, validation_labels) = train_test_split(ids_train, labels_train,
                                                     random_state=42,
                                                     test_size=0.1)
(train_masks, validation_masks,
 _, _) = train_test_split(amasks_train, ids_train,
                          random_state=42, test_size=0.1)

train_inputs = torch.tensor(train_inputs)
train_labels = torch.tensor(train_labels)
train_masks = torch.tensor(train_masks)
validation_inputs = torch.tensor(validation_inputs)
validation_labels = torch.tensor(validation_labels)
validation_masks = torch.tensor(validation_masks)
test_inputs = torch.tensor(ids_test)
test_labels = torch.tensor(labels_test)
test_masks = torch.tensor(amasks_test)


# %%
# Next we create PyTorch DataLoaders for all data sets.
#
# For fine-tuning BERT on a specific task, the authors recommend a
# batch size of 16 or 32.

BATCH_SIZE = 32

print('Train: ', end="")
train_data = TensorDataset(train_inputs, train_masks,
                           train_labels)
train_sampler = RandomSampler(train_data)
train_dataloader = DataLoader(train_data, sampler=train_sampler,
                              batch_size=BATCH_SIZE)
print(len(train_data), 'messages')

print('Validation: ', end="")
validation_data = TensorDataset(validation_inputs, validation_masks,
                                validation_labels)
validation_sampler = SequentialSampler(validation_data)
validation_dataloader = DataLoader(validation_data,
                                   sampler=validation_sampler,
                                   batch_size=BATCH_SIZE)
print(len(validation_data), 'messages')

print('Test: ', end="")
test_data = TensorDataset(test_inputs, test_masks, test_labels)
test_sampler = SequentialSampler(test_data)
test_dataloader = DataLoader(test_data, sampler=test_sampler,
                             batch_size=BATCH_SIZE)
print(len(test_data), 'messages')


# %%
# ## BERT model initialization
#
# We now load a pretrained BERT model with a single linear
# classification layer added on top.

print('Initializing BertForSequenceClassification')

model = BertForSequenceClassification.from_pretrained(BERTMODEL,
                                                      cache_dir=CACHE_DIR,
                                                      num_labels=20)
model.cuda()


# %%
# We set the remaining hyperparameters needed for fine-tuning the
# pretrained model:
#   * EPOCHS: the number of training epochs in fine-tuning
#     (recommended values between 2 and 4)
#   * WEIGHT_DECAY: weight decay for the Adam optimizer
#   * LR: learning rate for the Adam optimizer (2e-5 to 5e-5 recommended)
#   * WARMUP_STEPS: number of warmup steps to (linearly) reach the set
#     learning rate
#
# We also need to grab the training parameters from the pretrained model.

EPOCHS = 16
WEIGHT_DECAY = 0.01
LR = 2e-5
WARMUP_STEPS = int(0.2*len(train_dataloader))

no_decay = ['bias', 'LayerNorm.weight']
optimizer_grouped_parameters = [
    {'params': [p for n, p in model.named_parameters()
                if not any(nd in n for nd in no_decay)],
     'weight_decay': WEIGHT_DECAY},
    {'params': [p for n, p in model.named_parameters()
                if any(nd in n for nd in no_decay)],
     'weight_decay': 0.0}
]
optimizer = AdamW(optimizer_grouped_parameters, lr=LR, eps=1e-8)
scheduler = get_linear_schedule_with_warmup(optimizer,
                                            num_warmup_steps=WARMUP_STEPS,
                                            num_training_steps=len(train_dataloader)*EPOCHS)


# %%

# If there's a GPU available...
if torch.cuda.is_available():

    # Tell PyTorch to use the GPU.
    device = torch.device("cuda")

    print('There are %d GPU(s) available.' % torch.cuda.device_count())

    print('We will use the GPU:', torch.cuda.get_device_name(0))

# If not...
else:
    print('No GPU available, using the CPU instead.')
    device = torch.device("cpu")


# %%
# ## Learning
#
# Let's now define functions to train() and evaluate() the model:

def train(epoch, loss_vector=None, log_interval=200):
    # Set model to training mode
    model.train()

    # Loop over each batch from the training set
    for step, batch in enumerate(train_dataloader):

        # Copy data to GPU if needed
        batch = tuple(t.to(device) for t in batch)

        # Unpack the inputs from our dataloader
        b_input_ids, b_input_mask, b_labels = batch

        # Zero gradient buffers
        optimizer.zero_grad()

        # Forward pass
        outputs = model(b_input_ids, token_type_ids=None,
                        attention_mask=b_input_mask, labels=b_labels)

        loss = outputs[0]
        if loss_vector is not None:
            loss_vector.append(loss.item())

        # Backward pass
        loss.backward()

        # Update weights
        optimizer.step()
        scheduler.step()

        if step % log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, step * len(b_input_ids),
                len(train_dataloader.dataset),
                100. * step / len(train_dataloader), loss))


def evaluate(loader):
    model.eval()

    n_correct, n_all = 0, 0

    for batch in loader:
        batch = tuple(t.to(device) for t in batch)
        b_input_ids, b_input_mask, b_labels = batch

        with torch.no_grad():
            outputs = model(b_input_ids, token_type_ids=None,
                            attention_mask=b_input_mask)
            logits = outputs[0]

        logits = logits.detach().cpu().numpy()
        predictions = np.argmax(logits, axis=1)

        labels = b_labels.to('cpu').numpy()
        n_correct += np.sum(predictions == labels)
        n_all += len(labels)

    print('Accuracy: [{}/{}] {:.4f}\n'.format(n_correct,
                                              n_all,
                                              n_correct/n_all))

# Now we are ready to train our model using the train()
# function. After each epoch, we evaluate the model using the
# validation set and evaluate().


train_lossv = []
for epoch in range(1, EPOCHS + 1):
    train(epoch, train_lossv)
    print('\nValidation set:')
    evaluate(validation_dataloader)

# ## Inference
#
# For a better measure of the quality of the model, let's see the
# model accuracy for the test messages.

print('Test set:')
evaluate(test_dataloader)
