import random

import librosa
import numpy as np
from paddle.io import Dataset


# 加载并预处理音频
def load_audio(audio_path, feature_method='melspectrogram', mode='train', sr=16000, chunk_duration=3):
    # 读取音频数据
    wav, sr_ret = librosa.load(audio_path, sr=sr)
    # 随机裁剪
    if mode == 'train':
        num_wav_samples = wav.shape[0]
        num_chunk_samples = int(chunk_duration * sr)
        if num_wav_samples > num_chunk_samples + 1:
            start = random.randint(0, num_wav_samples - num_chunk_samples - 1)
            stop = start + num_chunk_samples
            wav = wav[start:stop]
    else:
        # 为避免显存溢出，只裁剪指定长度
        num_wav_samples = wav.shape[0]
        num_chunk_samples = int(chunk_duration * sr)
        if num_wav_samples > num_chunk_samples + 1:
            wav = wav[:num_chunk_samples]
    # 获取音频特征
    if feature_method == 'melspectrogram':
        # 计算梅尔频谱
        features = librosa.feature.melspectrogram(y=wav, sr=sr, n_fft=400, n_mels=80, hop_length=160, win_length=400)
    elif feature_method == 'spectrogram':
        # 计算声谱图
        linear = librosa.stft(wav, n_fft=400, win_length=400, hop_length=160)
        features, _ = librosa.magphase(linear)
    else:
        raise Exception(f'预处理方法 {feature_method} 不存在！')
    features = librosa.power_to_db(features, ref=1.0, amin=1e-10, top_db=None)
    mean = np.mean(features, 0, keepdims=True)
    std = np.std(features, 0, keepdims=True)
    features = (features - mean) / (std + 1e-5)
    return features


# 数据加载器
class CustomDataset(Dataset):
    def __init__(self, data_list_path, feature_method='melspectrogram', mode='train', sr=16000, chunk_duration=3):
        super(CustomDataset, self).__init__()
        if data_list_path is not None:
            with open(data_list_path, 'r') as f:
                self.lines = f.readlines()
        self.feature_method = feature_method
        self.mode = mode
        self.sr = sr
        self.chunk_duration = chunk_duration

    def __getitem__(self, idx):
        audio_path, label = self.lines[idx].replace('\n', '').split('\t')
        # 加载并预处理音频
        features = load_audio(audio_path, feature_method=self.feature_method,
                              mode=self.mode, sr=self.sr, chunk_duration=self.chunk_duration)
        return features, np.array(int(label), dtype=np.int64)

    def __len__(self):
        return len(self.lines)

    @property
    def input_size(self):
        if self.feature_method == 'melspectrogram':
            return 80
        elif self.feature_method == 'spectrogram':
            return 201
        else:
            raise Exception(f'预处理方法 {self.feature_method} 不存在！')


# 对一个batch的数据处理
def collate_fn(batch):
    # 找出音频长度最长的
    batch = sorted(batch, key=lambda sample: sample[0].shape[1], reverse=True)
    freq_size = batch[0][0].shape[0]
    max_audio_length = batch[0][0].shape[1]
    batch_size = len(batch)
    # 以最大的长度创建0张量
    inputs = np.zeros((batch_size, freq_size, max_audio_length), dtype='float32')
    input_lens = []
    labels = []
    for x in range(batch_size):
        sample = batch[x]
        tensor = sample[0]
        labels.append(sample[1])
        seq_length = tensor.shape[1]
        # 将数据插入都0张量中，实现了padding
        inputs[x, :, :seq_length] = tensor[:, :]
        input_lens.append(seq_length)
    input_lens = np.array(input_lens, dtype='float32')
    labels = np.array(labels, dtype='int64')
    # 打乱数据
    return inputs, labels, input_lens
