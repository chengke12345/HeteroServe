除了模型推理的性能之外，还需要对模型推理的质量进行评估。我们主要对模型在在中文语境下的知识和推理能力进行评估。
# 1. 评估测试数据集

对部署模型进行质量评估时，我们使用 C-Eval 中文考试评测集。这个数据集是给大语言模型做中文知识/考试能力评测用的。

C-Eval 的全称是 C-Eval: A Multi-Level Multi-Discipline Chinese Evaluation Suite for Fundation Models. 包含中文单项选择题，覆盖 52 个学科，中学/高中/大学/职业 等多个难度层级。
它主要用于评估基础模型在中文语境下的知识和推理能力。

我们从 Hugging Face 上下载数据。

```python
ds = load_dataset('ceval/ceval-exam', subject, split="val")
```
- `"ceval/ceval-exam"` 是 Hugging Face 上的数据仓库，属于 C-Eval benchmark
- `split="val"` 我们只加载了验证集，validation split。验证集是有问题与对应答案的测试数据。除此之外，还有测试集 test split.
- `subject`, 表示具体科目，C-Eval 共有 52 个科目，一共 1364 个题目或者测试用例。

C-Eval 测试集，完整52个科目，及每个科目对应的验证集 val split, 测试集 test split, 如下：

| 科目ID                                       | 中文名                  | val      | test      | 总数        |
| ------------------------------------------ | -------------------- | -------- | --------- | --------- |
| `accountant`                               | 注册会计师                | 49       | 443       | 497       |
| `advanced_mathematics`                     | 高等数学                 | 19       | 173       | 197       |
| `art_studies`                              | 艺术学                  | 33       | 298       | 336       |
| `basic_medicine`                           | 基础医学                 | 19       | 175       | 199       |
| `business_administration`                  | 工商管理                 | 33       | 301       | 339       |
| `chinese_language_and_literature`          | 中国语言文学               | 23       | 209       | 237       |
| `civil_servant`                            | 公务员                  | 47       | 429       | 481       |
| `clinical_medicine`                        | 临床医学                 | 22       | 200       | 227       |
| `college_chemistry`                        | 大学化学                 | 24       | 224       | 253       |
| `college_economics`                        | 大学经济学                | 55       | 497       | 557       |
| `college_physics`                          | 大学物理                 | 19       | 176       | 200       |
| `college_programming`                      | 大学编程                 | 37       | 342       | 384       |
| `computer_architecture`                    | 计算机组成                | 21       | 193       | 219       |
| `computer_network`                         | 计算机网络                | 19       | 171       | 195       |
| `discrete_mathematics`                     | 离散数学                 | 16       | 153       | 174       |
| `education_science`                        | 教育学                  | 29       | 270       | 304       |
| `electrical_engineer`                      | 注册电气工程师              | 37       | 339       | 381       |
| `environmental_impact_assessment_engineer` | 环境影响评价工程师            | 31       | 281       | 317       |
| `fire_engineer`                            | 注册消防工程师              | 31       | 282       | 318       |
| `high_school_biology`                      | 高中生物                 | 19       | 175       | 199       |
| `high_school_chemistry`                    | 高中化学                 | 19       | 172       | 196       |
| `high_school_chinese`                      | 高中语文                 | 19       | 178       | 202       |
| `high_school_geography`                    | 高中地理                 | 19       | 178       | 202       |
| `high_school_history`                      | 高中历史                 | 20       | 182       | 207       |
| `high_school_mathematics`                  | 高中数学                 | 18       | 166       | 189       |
| `high_school_physics`                      | 高中物理                 | 19       | 175       | 199       |
| `high_school_politics`                     | 高中政治                 | 19       | 176       | 200       |
| `ideological_and_moral_cultivation`        | 思想道德修养与法律基础          | 19       | 172       | 196       |
| `law`                                      | 法学                   | 24       | 221       | 250       |
| `legal_professional`                       | 法律职业资格               | 23       | 215       | 243       |
| `logic`                                    | 逻辑学                  | 22       | 204       | 231       |
| `mao_zedong_thought`                       | 毛泽东思想和中国特色社会主义理论体系概论 | 24       | 219       | 248       |
| `marxism`                                  | 马克思主义基本原理            | 19       | 179       | 203       |
| `metrology_engineer`                       | 注册计量师                | 24       | 219       | 248       |
| `middle_school_biology`                    | 初中生物                 | 21       | 192       | 218       |
| `middle_school_chemistry`                  | 初中化学                 | 20       | 185       | 210       |
| `middle_school_geography`                  | 初中地理                 | 12       | 108       | 125       |
| `middle_school_history`                    | 初中历史                 | 22       | 207       | 234       |
| `middle_school_mathematics`                | 初中数学                 | 19       | 177       | 201       |
| `middle_school_physics`                    | 初中物理                 | 19       | 178       | 202       |
| `middle_school_politics`                   | 初中政治                 | 21       | 193       | 219       |
| `modern_chinese_history`                   | 近代史纲要                | 23       | 212       | 240       |
| `operating_system`                         | 操作系统                 | 19       | 179       | 203       |
| `physician`                                | 医师资格                 | 49       | 443       | 497       |
| `plant_protection`                         | 植物保护                 | 22       | 199       | 226       |
| `probability_and_statistics`               | 概率统计                 | 18       | 166       | 189       |
| `professional_tour_guide`                  | 导游资格                 | 29       | 266       | 300       |
| `sports_science`                           | 体育学                  | 19       | 180       | 204       |
| `tax_accountant`                           | 税务师                  | 49       | 443       | 497       |
| `teacher_qualification`                    | 教师资格                 | 44       | 399       | 448       |
| `urban_and_rural_planner`                  | 注册城乡规划师              | 46       | 418       | 469       |
| `veterinary_medicine`                      | 兽医学                  | 23       | 210       | 238       |
| **合计**                                     | 52科                  | **1346** | **12342** | **13948** |

数据集中的每个题目都给出了，问题描述，选项，正确答案：

```json
{
    "id": 0,
    "question": "使用位填充方法，以01111110为位首flag，数据为...",
    "A": "1",
    "B": "2",
    "C": "3",
    "D": "4",
    "answer": "C",
    "explanation": ""
}
```


# 2. 核心指标

质量评估测试时，我们将问题和选项提取出来，发送给大模型，让模型返回推理后得到的答案。然后我们将模型返回答案与数据集中的正确答案进行对比。然后用回答正确的题目数与总题目数做对比，得到正确率。

### 一、正确率(Acc, Accuarcy)

正确率作为模型推理质量的主要评估指标，即
$$
acc = \frac{correct}{total}\times 100\%
$$


测试时，我们会对 Qwen3-32B-AWQ, Qwen3-14B-FP16, Qwen3-32B-GPTQ 三个模型在 thinking 和 nonthinking 模式下，分别在 val split 验证集上完整跑完 52 个科目的 1364 个测试用例。
在 non-thinking 模式下, 三个模型跑完完整的 52个科目，12342个测试集数据。

让每个模型在每个模式、每个数据集下，分别跑出测试数据。统计整体正确率与各科目下正确率。

### 二、macro avg VS micro avg

正确率的统计分两种 macro average 和 micro average。 

macro average 是分别计算每一个科目的正确率，然后再求所有科目的平均正确率, 也就是说，所有科目的权重相同，不管这个科目中的有多少个测试题。

micro average 是把所有科目的答对题数加起来，再除以所有题目总数。每道题权重相同，题量大的科目影响更大。

两个统计指标，都具备很高的参考价值。

# 3. 测试结果与分析

### 一、测试单个 subject 

首先，在单个 subject 上进行测试，选用 `“computer_network”`科目。完整测试脚本，详见 [15-EXP4-eval_quality_subject.py](/scripts/15-EXP4-eval_quality_subject.py)

单个 `“computer_network”` subject 的测试结果如下：

|                   | Qwen3-32B-AWQ | Qwen3-14B-FP16 | Qwen3-32B-GPTQ |
| ----------------- | ------------- | -------------- | -------------- |
| acc(no thinking)  | 0.684         | 0.737          | 0.684          |
| acc(thinking)     | 0.895         | 0.895          | 0.842          |
| time(no thinking) | 12.45         | 11.03          | 14.12          |
| time(thinking)    | 1270.08       | 953.19         | 1339.7         |
测试结果，详见 [computer_network_qwen3-32b-awq.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/computer_network_qwen3-32b-awq.json), [computer_network_qwen3-14b-fp16.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/computer_network_qwen3-14b-fp16.json), [computer_network_qwen3-32b-gptq.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/computer_network_qwen3-32b-gptq.json)

#### 结果分析

在`computer_network`单个subject上，non-thinking 模式下与 thinking 模式下的表现，有明显差距。在 thinking 模式下 AWQ 能达到 89.5%的准确率，与 FP16 差不多，略好于 GPTQ。但是non-thinking模式下，AWQ和GPTQ的准确率为 68.4%，略差于 FP16 的 73.7%。量化精度对模型表现产生了影响。

在 thinking 和 non-thinking 模式下，模型跑完`computer_network`上仅有的 19个 测试用例，所使用的时间，就形成了巨大差异。Qwen3-32B-AWQ 在 non-thinking 模式下跑完 19 个问题，用了12.45秒，而在 thinking 模式下用了 1270.08 秒，呈现出100倍的推理时间上的差异。GPTQ 与 FP16 的推理时间上也呈现出类似的相关性。

> 注意⚠️：这只是单个 `computer_network`subject 下仅仅19个问题呈现出来的准确率结果，反应出的模型推理质量问题有限。但是在推理时间上的表现，已经能够说明问题和规律。

### 二、C-Eval 完整验证集(val)测试

我们在 C-Eval 的完整验证集上进行测试，即`split="val"`。验证集包含 52个 科目，共 1364 个题目/测试用例。
完整验证集的测试脚本，详见[14-EXP4-eval_quality_all.py](/scripts/14-EXP4-eval_quality_all.py)

在 thinking 和 non-thinking 模式下分别进行测试

|                                  | Macro Avg % | Micro Avg % | correct | total | subjects | serial tput <br>(tok/s) |
| -------------------------------- | ----------- | ----------- | ------- | ----- | -------- | ----------------------- |
| Qwen3-32B-AWQ<br>(non-thinking)  | 82.70       | 82.47       | 1110    | 1346  | 52       | 4.2                     |
| Qwen3-32B-AWQ<br>(thinking)      | 85.20       | 84.03       | 1131    | 1346  | 52       | 27.8                    |
| Qwen3-14B-FP16<br>(non-thinking) | 79.22       | 78.68       | 1059    | 1346  | 52       | 6.5                     |
| Qwen3-14B-FP16<br>(thinking)     | 82.50       | 80.91       | 1089    | 1346  | 52       | 35.6                    |
| Qwen3-32B-GPTQ<br>(non-thinking) | 82.10       | 81.72       | 1100    | 1346  | 52       | 4.2                     |
| Qwen3-32B-GPTQ<br>(thinking)     | 84.2        | 83.0        | 1116    | 1346  | 52       | 27.2                    |

关于每个 subject 的正确率以及详细的测试结果，详见测试产生的 json 数据结果：

non-thinking 模式下，详见[ceval_val_qwen3-32b-awq_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-32b-awq_nonthinking.json), [ceval_qwen3-14b-fp16_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-14b-fp16_nonthinking.json),  [ceval_val_qwen3-32b-gptq_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-32b-gptq_nonthinking.json)

thinking 模式下，详见[ceval_val_qwen3-32b-awq_thinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-32b-awq_thinking.json), [ceval_val_qwen3-14b-fp16_thinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-14b-fp16_thinking.json), [ceval_val_qwen3-32b-gptq_thinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_val_qwen3-32b-gptq_thinking.json)

每个模型测试产生的 json 测试数据文件，包含所有52个科目下，一共 1364 个题目上的整体测试数据，以及以及分别在每个科目下的测试数据。一共有 6 个测试数据文件。

每个模型，都采用了 thinking  和 nonthinking 两种模型访问模式，对比评估两种模式下，模型回答问题的正确率差别多大。thinking 模式下，我们只对 val 验证集进行了测试。一共52个科目，1364个测试题目/用例。

在 thinking模式下，我们跑完整的 val 验证集，每个模型大约需要跑～1.5天，而 non-thinking 模式下，每个模型大约需要 ～30分钟。

### 结果分析

在 val 验证集下，每个模型都在 thinking 和 non-thinking 模式下，跑完了 52个科目 1364个测试问题/用例。 6个 json 数据文件中存放了每个模型在每个模式下的表现。统计整体与各个科目下的表现。matplotlib 将测试数据表示成直方图：

Qwen3-32B-AWQ (non-thinking) split='val' VS Qwen3-14B-FP16 VS Qwen3-32B-GPTQ 
![](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-awq_nonthinking_qwen3-32b-awq_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_val_qwen3-14b-fp16_nonthinking_qwen3-14b-fp16_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-gptq_nonthinking_qwen3-32b-gptq_stacked_subject_bars.png)

直方图数据柱代表科目，总共 52 个数据柱，表示52个科目。粉红色部分代表了该科目下的测试题目数，绿色代表模型推理正确的题目数。柱顶文字标明了正确率。

三个模型表现最差的科目比较一致，都是高中数学`high school mathematics` ， 高等数学 `advanced mathematics` 和 离散数学 `discrete mathematics`. 

以 AWQ 模型为例说明，在`high school mathematics` 上正确率只有 44.4%, 18题答对了8题，在`high school mathematics` 上正确率只有 52.6%，19题只答对10题，表现第三差的是 `discrete mathematics`，正确率 56.3%, 16题只答对9题。 

AWQ 和 GPTQ 表现最好的科目是 `high school biology` 和 `ideological and moral cultivation`。两个模型都答对了全部的测试题目，正确率100%. 而 FP16 模型表现最好的是 `middle school politics`，答对全部测试题，正确率 100%.

所以 Qwen3 的这三个模型，都不擅长进行数学推理，解数学题，而更擅长人文科学类的问题。

thinking模式下

Qwen3-32B-AWQ (thinking) split='val' VS Qwen3-14B-FP16 VS Qwen3-32B-GPTQ 
![](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-awq_thinking_qwen3-32b-awq_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_val_qwen3-14b-fp16_thinking_qwen3-14b-fp16_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-gptq_thinking_qwen3-32b-gptq_stacked_subject_bars.png)


关于 val 验证集上完整，数据统计直方图可以参看如下：

nonthinking 模式下：
[ceval_val_qwen3-32b-awq_nonthinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-awq_nonthinking_qwen3-32b-awq_stacked_subject_bars.png),
[ceval_val_qwen3-14b-fp16_nonthinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-14b-fp16_nonthinking_qwen3-14b-fp16_stacked_subject_bars.png), 
[ceval_val_qwen3-32b-gptq_nonthinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-gptq_nonthinking_qwen3-32b-gptq_stacked_subject_bars.png)

thinking 模式下：
[ceval_val_qwen3-32b-awq_thinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-awq_thinking_qwen3-32b-awq_stacked_subject_bars.png)
[ceval_val_qwen3-14b-fp16_thinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-14b-fp16_thinking_qwen3-14b-fp16_stacked_subject_bars.png)
[ceval_val_qwen3-32b-gptq_thinking.png](/docs/assets/EXP4_assets/ceval_val_qwen3-32b-gptq_thinking_qwen3-32b-gptq_stacked_subject_bars.png)

thinking 模式相对 non-thinking 模式来说，在 C-Eval 评测集上，推理正确率有一定的提升，但是不是特别巨大。但是 thinking 模式相对于 non-thinking 模式的推理速度慢100倍。是否值得开启，因情况而定。

### 三、C-Eval 完整测试集(test)测试

我们在 C-Eval 的完整测试集上进行测试，即 `split="test"`。测试集包含 52个科目，12342个题目/测试用例。在测试集上，三个模型我们都只在 non-thinking 模式下进行测试。

thinking 模式 与 non-thinking 模式在模型质量上的对比，在 val 验证集上的测试表现，已经能够得出结论。而在 test 测试集上，52个科目，有完整的 12342 个测试题目/用例。在本项目的硬件条件下，完整测试 thinking 模式，在时间开销上不现实。

non-thinking 模式下，我们把 test 集上测试得到的数据，与 val 集上得到的数据，进行对比：

|                                       | Macro Avg % | Micro Avg % | correct | total | subjects | serial tput <br>(tok/s) |
| ------------------------------------- | ----------- | ----------- | ------- | ----- | -------- | ----------------------- |
| Qwen3-32B-AWQ_test<br>(non-thinking)  | 80.1        | 79.6        | 9826    | 12342 | 52       | 8.7                     |
| Qwen3-14B-FP16_test<br>(non-thinking) | 77.5        | 76.9        | 9495    | 12342 | 52       | 14.2                    |
| Qwen3-32B-GPTQ_test<br>(non-thinking) | 80.1        | 79.6        | 9827    | 12342 | 52       | 7.1                     |
| Qwen3-32B-AWQ_val<br>(non-thinking)   | 82.70       | 82.47       | 1110    | 1346  | 52       | 4.2                     |
| Qwen3-14B-FP16_val<br>(non-thinking)  | 79.22       | 78.68       | 1059    | 1346  | 52       | 6.5                     |
| Qwen3-32B-GPTQ_val<br>(non-thinking)  | 82.10       | 81.72       | 1100    | 1346  | 52       | 4.2                     |

在 `split="test"` 测试集上，完整测试三个模型的详细测试数据，参见 [ceval_test_qwen3-32b-awq_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_test_qwen3-32b-awq_nonthinking.json), [ceval_test_qwen3-14b-fp16_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_test_qwen3-14b-fp16_nonthinking.json), [ceval_test_qwen3-32b-gptq_nonthinking.json](/logs%20&%20reports/07-EXP4-ceval_quality_evaluations/ceval_test_qwen3-32b-gptq_nonthinking.json) .

在 test 测试集上，nonthinking 模式下，我们看到三个模型在每个科目下的表现为

nonthinking, split = 'test' Qwen3-32B-AWQ VS Qwen3-14B-FP16 VS Qwen3-32B-GPTQ
![](/docs/assets/EXP4_assets/ceval_test_qwen3-32b-awq_nonthinking_qwen3-32b-awq_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_test_qwen3-14b-fp16_nonthinking_qwen3-14b-fp16_stacked_subject_bars.png)
![](/docs/assets/EXP4_assets/ceval_test_qwen3-32b-gptq_nonthinking_qwen3-32b-gptq_stacked_subject_bars.png)

对于 test 测试集来说，它的样本空间更大，一共12342个测试用例。而 val 验证集有1364个测试用例。test 测试集的测试结果，更接近客观事实规律。

# 4. 质量-性能 Pareto图

我们从全局测试数据考虑，根据测试结果的 json 测试数据，可以画出 Pareto 图。
test 测试集下 non-thinking 模式的 Pareto 图： 

在test 测试集上，nonthinking模式的三个模型质量-性能 Pareto 图
![image|500](/docs/assets/EXP4_assets/quality_perf_pareto_test_nonthinking.png)

在 val 验证集上，nonthinking模式的三个模型质量-性能 Pareto 图
![image|500](/docs/assets/EXP4_assets/quality_perf_pareto_val_nonthinking.png)

在 val 验证集上，thinking模式的三个模型质量-性能 Pareto 图
![image | 500](/docs/assets/EXP4_assets/quality_perf_pareto_val_thinking.png)

# 5. 结论

- 三个模型在C-Eval评测集上的表现，在 val 和 test 集上，AWQ的推理正确率都略高于 GPTQ，但是它们俩远好于 FP16 的推理表现。
- 三个模型都不擅长数学推理和解数学题。更擅长人文科学方面的推理。
- 在 C-Eval 评测集上，thinking 模式与 non-thinking 模式正确率有一定的提升，但不是特别大。
- thinking 模式比 non-thinking 模式的推理速度，慢约 100 倍。是否值得开启 thinking 模式，需要根据实际情况，再确定。
- 三个模型在系统稳定性方面的表现都堪称完美。一共 52 个科目，val 验证集上 1364个测试用例，test 集上 12342 个测试用例，在 thinking 和 nonthinking 模式下运行，一共运行 45102 个测试用例。测试整体时间约 5 天。 测试案例全部顺利推理完成。0 失败。

<u>综上所述，Qwen3-32B-AWQ 是当前硬件条件下的最佳选择。</u>
