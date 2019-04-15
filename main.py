import model
import tensorflow as tf
from data import load_pieces, get_batch, build_vocab, tokenize
import numpy as np
import sys
from tqdm import tqdm
import hyper_params as hp
from midi_handler import noteStateMatrixToMidi

np.set_printoptions(threshold=sys.maxsize)


def train(model, pieces, epochs, save_name, start=0):
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())
    saver = tf.train.Saver()
    pbar = tqdm(range(start, start+epochs))
    # x, y = get_batch(pieces)
    # l = sess.run([model.prediction],
    #                 feed_dict={model.inputs: x,
    #                            model.labels: y})
    # print(x.shape)
    # print(y.shape)
    # print(l[0].shape)
    for i in pbar:
        x, y = get_batch(pieces)
        # print(x)
        # print(y)
        l, _ = sess.run([model.loss, model.optimize],
                        feed_dict={model.inputs: x,
                                   model.labels: y,
                                   model.dropout: hp.DROPOUT})
        # if i % 100 == 0:
        pbar.set_description("epoch {}, loss={}".format(i, l))
        if i % 100 == 0:
            print("epoch {}, loss={}".format(i, l))
        if i % 500 == 0:
            print("Saving at epoch {}, loss={}".format(i, l))
            saver.save(sess,
                       save_name + str(l),
                       global_step=i)
        if i % 1000 == 0:
            total_correct = 0
            total_symbols = 0
            for piece in pieces["train"]:
                x = np.expand_dims(piece[:-1], axis=0)
                y = np.expand_dims(piece[:-1], axis=0)
                prediction = sess.run(model.logits,
                                      feed_dict={model.inputs: x})
                # print(prediction)
                activation = np.argmax(prediction, axis=2)
                print("act: ", activation)
                print("lab: ", y)
                total_correct += np.sum(y == activation)
                total_symbols += activation.shape[1]
            print(total_correct / total_symbols)
    final_loss = sess.run([model.loss],
                          feed_dict={model.inputs: x,
                                     model.labels: y})
    saver.save(sess, save_name + str(final_loss[0]))


def test(model, pieces, save_name):
    sess = tf.Session()
    saver = tf.train.Saver()
    saver = tf.train.import_meta_graph(save_name + '.meta')
    saver.restore(sess, save_name)
    total_correct = 0
    total_symbols = 0
    for piece in pieces["test"]:
        x = np.expand_dims(piece[:-1], axis=0)
        y = np.expand_dims(piece[1:], axis=0)
        prediction = sess.run(model.prediction,
                              feed_dict={model.inputs: x})
        # print(prediction.shape)
        activation = np.argmax(prediction, axis=2)
        print(activation)
        print(y)
        total_correct += np.sum(y == activation)
        total_symbols += activation.shape[1]
    print(total_correct / total_symbols)


def generate(model,
             pieces,
             save_name,
             token2idx,
             idx2token,
             batch_size=10,
             length=1000):
    sess = tf.Session()
    saver = tf.train.Saver()
    saver = tf.train.import_meta_graph(save_name + '.meta')
    saver.restore(sess, save_name)
    x, _ = get_batch(pieces, 1)

    time_input = x
    for i in range(4, time_input.shape[1]):
        time_input[0][i] = token2idx[hp.PAD]
    # (batch_size, max_len, pitch_sz)
    composition = np.zeros((time_input.shape[0], int(time_input.shape[1] / 4), hp.NOTE_LEN))

    # pbar = tqdm(range(length))
    # print(time_input)
    for i in range(1, int(time_input.shape[1] / 4)):
        for j in range(4):
            # (batch_size, max_len, vocab_size)
            prediction = sess.run(model.prediction,
                                  feed_dict={model.inputs: time_input})
            # (batch_size, max_len)
            activation = np.argmax(prediction, axis=2)
            # print(activation)
            pitch = idx2token[activation[0][i*4 + j-1]] - 24
            # print(pitch)
            if pitch < hp.NOTE_LEN:
                composition[0][i][pitch] = 1

            time_input[0][i*4 + j] = activation[0][i*4 + j-1]
            # print(time_input)

    composition = np.reshape(np.tile(composition, (2)), (composition.shape[0], composition.shape[1], composition.shape[2], 2))

    for song_idx in range(composition.shape[0]):
        noteStateMatrixToMidi(composition[song_idx],
                              'output/sample_' + str(song_idx))


if __name__ == '__main__':
    inputs = tf.placeholder(tf.int32, shape=[None, hp.MAX_LEN])
    labels = tf.placeholder(tf.int32, shape=[None, hp.MAX_LEN])
    dropout = tf.placeholder(tf.float32)

    # pieces, seqlens = load_pieces("data/roll/jsb8.pkl")
    pieces, seqlens = load_pieces("data/roll/jsb4.pkl")
    token2idx, idx2token = build_vocab(pieces)
    pieces = tokenize(pieces, token2idx, idx2token)
    m = model.Model(inputs=inputs,
                    labels=labels,
                    dropout=dropout,
                    token2idx=token2idx,
                    idx2token=idx2token)
    train(m, pieces, 100000, "model/n/model_")
    # test(m, pieces, "model/cheating/model_0.00082397216-69000")
    # generate(m, pieces, "model/jsb8/model_0.008184661-189500", token2idx, idx2token)
