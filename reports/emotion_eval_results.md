# Emotion Evaluation Results

API available: True

- Overall correct/total: 58/60
- Overall accuracy: 0.967

## Per-label accuracy
- happy: 10/10 accuracy=1.000
- sad: 10/10 accuracy=1.000
- angry: 9/10 accuracy=0.900
- love: 10/10 accuracy=1.000
- fearful: 9/10 accuracy=0.900
- neutral: 10/10 accuracy=1.000

## Confusion matrix (gold -> pred)
|gold/pred|happy|sad|angry|love|fearful|neutral|
|---|---|---|---|---|---|---|
|happy|10|0|0|0|0|0|
|sad|0|10|0|0|0|0|
|angry|0|1|9|0|0|0|
|love|0|0|0|10|0|0|
|fearful|0|1|0|0|9|0|
|neutral|0|0|0|0|0|10|

## Misclassified examples

| id | text | gold | pred |
|---:|------|:----:|:----:|
| 1 | 이 상황이 너무 불공평해서 참을 수가 없어요. | angry | sad |
| 2 | 결과가 나쁘면 어떡하나 걱정돼서 잠을 못 자요. | fearful | sad |
