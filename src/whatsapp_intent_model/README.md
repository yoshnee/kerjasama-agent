---
tags:
- setfit
- sentence-transformers
- text-classification
- generated_from_setfit_trainer
widget:
- text: Hey there
- text: Hi there, I got your number from a friend and I want to book you
- text: Hi there, do you offer your services for large groups?
- text: What's your availability like for April 2026?
- text: Can you fit me in next Tuesday?
metrics:
- accuracy
pipeline_tag: text-classification
library_name: setfit
inference: true
base_model: answerdotai/ModernBERT-base
---

# SetFit with answerdotai/ModernBERT-base

This is a [SetFit](https://github.com/huggingface/setfit) model that can be used for Text Classification. This SetFit model uses [answerdotai/ModernBERT-base](https://huggingface.co/answerdotai/ModernBERT-base) as the Sentence Transformer embedding model. A [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance is used for classification.

The model has been trained using an efficient few-shot learning technique that involves:

1. Fine-tuning a [Sentence Transformer](https://www.sbert.net) with contrastive learning.
2. Training a classification head with features from the fine-tuned Sentence Transformer.

## Model Details

### Model Description
- **Model Type:** SetFit
- **Sentence Transformer body:** [answerdotai/ModernBERT-base](https://huggingface.co/answerdotai/ModernBERT-base)
- **Classification head:** a [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance
- **Maximum Sequence Length:** 8192 tokens
- **Number of Classes:** 4 classes
<!-- - **Training Dataset:** [Unknown](https://huggingface.co/datasets/unknown) -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Repository:** [SetFit on GitHub](https://github.com/huggingface/setfit)
- **Paper:** [Efficient Few-Shot Learning Without Prompts](https://arxiv.org/abs/2209.11055)
- **Blogpost:** [SetFit: Efficient Few-Shot Learning Without Prompts](https://huggingface.co/blog/setfit)

### Model Labels
| Label | Examples                                                                                                                                                                                                  |
|:------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0     | <ul><li>"I'm interested in booking your services for an event"</li><li>'Hi, I saw your work and want to inquire about a session'</li><li>"Hello, I'm looking for a professional for my wedding"</li></ul> |
| 1     | <ul><li>'Are you free on date?'</li><li>'Do you have availability on Monday?'</li><li>'Do you have any openings this coming Saturday?When are you available?'</li></ul>                                   |
| 2     | <ul><li>'What are your prices?'</li><li>'How much do you charge?'</li><li>"What are your rates?What's your rate?"</li></ul>                                                                               |
| 3     | <ul><li>'What are your business hours?'</li><li>'Are you open on Sundays?'</li><li>'Where is your studio located?'</li></ul>                                                                              |

## Uses

### Direct Use for Inference

First install the SetFit library:

```bash
pip install setfit
```

Then you can load this model and run inference.

```python
from setfit import SetFitModel

# Download from the 🤗 Hub
model = SetFitModel.from_pretrained("setfit_model_id")
# Run inference
preds = model("Hey there")
```

<!--
### Downstream Use

*List how someone could finetune this model on their own dataset.*
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Set Metrics
| Training set | Min | Median | Max |
|:-------------|:----|:-------|:----|
| Word count   | 1   | 7.9011 | 39  |

| Label | Training Sample Count |
|:------|:----------------------|
| 0     | 22                    |
| 1     | 17                    |
| 2     | 30                    |
| 3     | 22                    |

### Training Hyperparameters
- batch_size: (16, 16)
- num_epochs: (3, 3)
- max_steps: -1
- sampling_strategy: oversampling
- num_iterations: 20
- body_learning_rate: (2e-05, 1e-05)
- head_learning_rate: 0.01
- loss: CosineSimilarityLoss
- distance_metric: cosine_distance
- margin: 0.25
- end_to_end: False
- use_amp: False
- warmup_proportion: 0.1
- l2_weight: 0.01
- seed: 42
- eval_max_steps: -1
- load_best_model_at_end: False

### Training Results
| Epoch  | Step | Training Loss | Validation Loss |
|:------:|:----:|:-------------:|:---------------:|
| 0.0044 | 1    | 0.1492        | -               |
| 0.2193 | 50   | 0.2867        | -               |
| 0.4386 | 100  | 0.1017        | -               |
| 0.6579 | 150  | 0.0214        | -               |
| 0.8772 | 200  | 0.0016        | -               |
| 1.0965 | 250  | 0.0007        | -               |
| 1.3158 | 300  | 0.0007        | -               |
| 1.5351 | 350  | 0.0006        | -               |
| 1.7544 | 400  | 0.0005        | -               |
| 1.9737 | 450  | 0.0004        | -               |
| 2.1930 | 500  | 0.0004        | -               |
| 2.4123 | 550  | 0.0003        | -               |
| 2.6316 | 600  | 0.0003        | -               |
| 2.8509 | 650  | 0.0003        | -               |

### Framework Versions
- Python: 3.9.6
- SetFit: 1.1.3
- Sentence Transformers: 5.1.2
- Transformers: 4.57.3
- PyTorch: 2.8.0
- Datasets: 4.4.2
- Tokenizers: 0.22.1

## Citation

### BibTeX
```bibtex
@article{https://doi.org/10.48550/arxiv.2209.11055,
    doi = {10.48550/ARXIV.2209.11055},
    url = {https://arxiv.org/abs/2209.11055},
    author = {Tunstall, Lewis and Reimers, Nils and Jo, Unso Eun Seo and Bates, Luke and Korat, Daniel and Wasserblat, Moshe and Pereg, Oren},
    keywords = {Computation and Language (cs.CL), FOS: Computer and information sciences, FOS: Computer and information sciences},
    title = {Efficient Few-Shot Learning Without Prompts},
    publisher = {arXiv},
    year = {2022},
    copyright = {Creative Commons Attribution 4.0 International}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->