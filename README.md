# 前言
此版本为新版本，如想使用使用旧版本，请转到[V1.0版本](https://github.com/yeyupiaoling/VoiceprintRecognition-PaddlePaddle/tree/V1.0) ，本版本使用了EcapaTdnn模型等多个模型，和多种数据预处理方法，参考了人脸识别项目的做法[PaddlePaddle-MobileFaceNets](https://github.com/yeyupiaoling/PaddlePaddle-MobileFaceNets) ,使用了ArcFace Loss，ArcFace loss：Additive Angular Margin Loss（加性角度间隔损失函数），对特征向量和权重归一化，对θ加上角度间隔m，角度间隔比余弦间隔在对角度的影响更加直接。

使用环境：

 - Python 3.7
 - PaddlePaddle 2.2.2

# 模型下载
|    模型     |     预处理方法      |                          数据集                           | 类别数量 | 模型下载地址  |
|:---------:|:--------------:|:------------------------------------------------------:|:----:|:-------:|
| EcapaTdnn | melspectrogram | [中文语音语料数据集](https://github.com/fighting41love/zhvoice) | 3242 | [开发中]() |
| EcapaTdnn | melspectrogram |                         更大的数据集                         | 6235 | [开发中]() |


# 安装环境
1. 安装PaddlePaddle的GPU版本，如果已经安装过PaddlePaddle，测无需再次安装。
```shell
pip install paddlepaddle-gpu==2.2.2 -i https://mirrors.aliyun.com/pypi/simple/
```

2. 安装其他依赖库，命令如下，注意librosa的版本是0.9.1，旧版本的梅尔频谱计算方式不一样。
```shell
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

# Nvidia Jetson预测环境搭建

1. 安装PaddlePaddle的Inference预测库。
```shell
wget https://paddle-inference-lib.bj.bcebos.com/2.1.1-nv-jetson-jetpack4.4-all/paddlepaddle_gpu-2.1.1-cp36-cp36m-linux_aarch64.whl
pip3 install paddlepaddle_gpu-2.1.1-cp36-cp36m-linux_aarch64.whl
```

2. 安装scikit-learn依赖库。
```shell
git clone git://github.com/scikit-learn/scikit-learn.git
cd scikit-learn
pip3 install cython
git checkout 0.24.2
pip3 install --verbose --no-build-isolation --editable .
```

3. 安装其他依赖库。
```shell
pip3 install -r requirements.txt
```

4. 在Nvidia Jetson开发板上预测跟[本地预测](#本地预测) 一样，请查看这部分操作。

**注意：** [libsora和pyaudio安装出错解决办法](docs/faq.md)

# 创建数据
本教程笔者使用的是[中文语音语料数据集](https://github.com/fighting41love/zhvoice) ，这个数据集一共有3242个人的语音数据，有1130000+条语音数据。如果读者有其他更好的数据集，可以混合在一起使用，但要用python的工具模块aukit处理音频，降噪和去除静音。

首先是创建一个数据列表，数据列表的格式为`<语音文件路径\t语音分类标签>`，创建这个列表主要是方便之后的读取，也是方便读取使用其他的语音数据集，语音分类标签是指说话人的唯一ID，不同的语音数据集，可以通过编写对应的生成数据列表的函数，把这些数据集都写在同一个数据列表中。

在`create_data.py`写下以下代码，因为[中文语音语料数据集](https://github.com/fighting41love/zhvoice) 这个数据集是mp3格式的，作者发现这种格式读取速度很慢，所以笔者把全部的mp3格式的音频转换为wav格式，在创建数据列表之后，可能有些数据的是错误的，所以我们要检查一下，将错误的数据删除。执行下面程序完成数据准备。
```shell
python create_data.py
```

执行上面的程序之后，会生成以下的数据格式，如果要自定义数据，参考如下数据列表，前面是音频的相对路径，后面的是该音频对应的说话人的标签，就跟分类一样。
```
dataset/zhvoice/zhmagicdata/5_895/5_895_20170614203758.wav	3238
dataset/zhvoice/zhmagicdata/5_895/5_895_20170614214007.wav	3238
dataset/zhvoice/zhmagicdata/5_941/5_941_20170613151344.wav	3239
dataset/zhvoice/zhmagicdata/5_941/5_941_20170614221329.wav	3239
dataset/zhvoice/zhmagicdata/5_941/5_941_20170616153308.wav	3239
dataset/zhvoice/zhmagicdata/5_968/5_968_20170614162657.wav	3240
dataset/zhvoice/zhmagicdata/5_968/5_968_20170622194003.wav	3240
dataset/zhvoice/zhmagicdata/5_968/5_968_20170707200554.wav	3240
dataset/zhvoice/zhmagicdata/5_970/5_970_20170616000122.wav	3241
```

# 数据读取
使用librosa可以很方便计算音频的特征，如梅尔频谱的API为`librosa.feature.melspectrogram()`，输出的是numpy值，可以直接用PaddlePaddle训练和预测。跟梅尔频谱同样很重要的梅尔倒谱（MFCCs）更多用于语音识别中，对应的API为`librosa.feature.mfcc()`。声谱图分别使用`librosa.stft()`和`librosa.magphase()`实现。
```python
if feature_method == 'melspectrogram':
    # 计算梅尔频谱
    features = librosa.feature.melspectrogram(y=wav, sr=sr, n_fft=400, n_mels=80, hop_length=160, win_length=400)
elif feature_method == 'spectrogram':
    # 计算声谱图
    linear = librosa.stft(wav, n_fft=400, win_length=400, hop_length=160)
    features, _ = librosa.magphase(linear)
```


# 训练模型
创建`train.py`开始训练模型，使用的是经过修改过的`resnet34`模型，数据输入层设置为`[None, 1, 257, 257]`，这个大小就是短时傅里叶变换的幅度谱的shape，如果读者使用了其他的语音长度，也需要修改这个值。每训练一轮结束之后，执行一次模型评估，计算模型的准确率，以观察模型的收敛情况。同样的，每一轮训练结束保存一次模型，分别保存了可以恢复训练的模型参数，也可以作为预训练模型参数。还保存预测模型，用于之后预测。
```shell
# 单卡训练
CUDA_VISIBLE_DEVICES=0 python train.py
# 多卡训练
python -m paddle.distributed.launch --gpus '0,1' train.py
```

训练过程中，会使用VisualDL保存训练日志，通过启动VisualDL可以随时查看训练结果，启动命令`visualdl --logdir=log --host 0.0.0.0`

# 评估模型
训练结束之后会保存预测模型，我们用预测模型来预测测试集中的音频特征，然后使用音频特征进行两两对比，阈值从0到1,步长为0.01进行控制，找到最佳的阈值并计算准确率。
```shell
python eval.py
```

输出类似如下：
```shell
-----------  Configuration Arguments -----------
feature_method: melspectrogram
list_path: dataset/test_list.txt
model_path: models/infer/model
------------------------------------------------

开始提取全部的音频特征...
100%|█████████████████████████████████████████████████████| 5332/5332 [01:09<00:00, 77.06it/s]
开始两两对比音频特征...
100%|█████████████████████████████████████████████████████| 5332/5332 [01:43<00:00, 51.62it/s]
100%|█████████████████████████████████████████████████████| 100/100 [00:03<00:00, 28.04it/s]
当阈值为0.700000, 准确率最大，准确率为：0.999950
```

# 导出模型
训练完模型之后，需要导出模型才能预测，执行下面命令导出模型。
```shell
python export_model.py
```

输出如下：
```shell
[2021-11-08 22:24:25.053515] 成功加载模型参数和优化方法参数
[2021-11-08 22:24:26.405506] 模型导出成功：models/infer/model
```

# 声纹对比
下面开始实现声纹对比，创建`infer_contrast.py`程序，编写`infer()`函数，在编写模型的时候，模型是有两个输出的，第一个是模型的分类输出，第二个是音频特征输出。所以在这里要输出的是音频的特征值，有了音频的特征值就可以做声纹识别了。我们输入两个语音，通过预测函数获取他们的特征数据，使用这个特征数据可以求他们的对角余弦值，得到的结果可以作为他们相识度。对于这个相识度的阈值`threshold`，读者可以根据自己项目的准确度要求进行修改。
```shell
python infer_contrast.py --audio_path1=audio/a_1.wav --audio_path2=audio/b_2.wav
```

输出类似如下：
```
-----------  Configuration Arguments -----------
audio_path1: audio/a_1.wav
audio_path2: audio/b_2.wav
feature_method: melspectrogram
model_path: models/infer/model
threshold: 0.7
------------------------------------------------

audio/a_1.wav 和 audio/b_2.wav 不是同一个人，相似度为：0.020499
```

# 声纹识别
在上面的声纹对比的基础上，我们创建`infer_recognition.py`实现声纹识别。同样是使用上面声纹对比的`infer()`预测函数，通过这两个同样获取语音的特征数据。 不同的是笔者增加了`load_audio_db()`和`register()`，以及`recognition()`，第一个函数是加载声纹库中的语音数据，这些音频就是相当于已经注册的用户，他们注册的语音数据会存放在这里，如果有用户需要通过声纹登录，就需要拿到用户的语音和语音库中的语音进行声纹对比，如果对比成功，那就相当于登录成功并且获取用户注册时的信息数据。第二个函数`register()`其实就是把录音保存在声纹库中，同时获取该音频的特征添加到待对比的数据特征中。最后`recognition()`函数中，这个函数就是将输入的语音和语音库中的语音一一对比。
有了上面的声纹识别的函数，读者可以根据自己项目的需求完成声纹识别的方式，例如笔者下面提供的是通过录音来完成声纹识别。首先必须要加载语音库中的语音，语音库文件夹为`audio_db`，然后用户回车后录音3秒钟，然后程序会自动录音，并使用录音到的音频进行声纹识别，去匹配语音库中的语音，获取用户的信息。通过这样方式，读者也可以修改成通过服务请求的方式完成声纹识别，例如提供一个API供APP调用，用户在APP上通过声纹登录时，把录音到的语音发送到后端完成声纹识别，再把结果返回给APP，前提是用户已经使用语音注册，并成功把语音数据存放在`audio_db`文件夹中。
```shell
python infer_recognition.py
```

输出类似如下：
```
-----------  Configuration Arguments -----------
audio_db: audio_db
feature_method: melspectrogram
model_path: models/infer/model
threshold: 0.7
------------------------------------------------

Loaded 李达康 audio.
Loaded 沙瑞金 audio.
请选择功能，0为注册音频到声纹库，1为执行声纹识别：0
按下回车键开机录音，录音3秒中：
开始录音......
录音已结束!
请输入该音频用户的名称：夜雨飘零
请选择功能，0为注册音频到声纹库，1为执行声纹识别：1
按下回车键开机录音，录音3秒中：
开始录音......
录音已结束!
识别说话的为：夜雨飘零，相似度为：0.920434
```

# 其他版本
 - Tensorflow：[VoiceprintRecognition-Tensorflow](https://github.com/yeyupiaoling/VoiceprintRecognition-Tensorflow)
 - Pytorch：[VoiceprintRecognition-Pytorch](https://github.com/yeyupiaoling/VoiceprintRecognition-Pytorch)
 - Keras：[VoiceprintRecognition-Keras](https://github.com/yeyupiaoling/VoiceprintRecognition-Keras)


# 参考资料
1. https://github.com/PaddlePaddle/PaddleSpeech
2. https://github.com/yeyupiaoling/PaddlePaddle-MobileFaceNets
