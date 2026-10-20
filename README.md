# Clothing classification

EfficientNet-B0 clothing classification with a training/evaluation notebook and an optional Lamoda image scraper.

## Setup

Use Python 3.12. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
jupyter lab
```

For a smaller CPU-only PyTorch installation, install the matching wheels before the requirements:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.9.1 torchvision==0.24.1
python -m pip install -r requirements.txt
```

A compatible CUDA installation is optional. The notebook automatically selects CUDA when available and otherwise uses CPU. The first model construction downloads ImageNet pretrained weights from `download.pytorch.org`.

## Dataset (external)

Images are intentionally excluded from this checkout. Download the dataset separately:

[Google Drive dataset](https://drive.google.com/drive/folders/1BHJGrRlsrOMpv5aqtsSZ_RtBRZdJXY_V?usp=sharing)

Extract it into this structure, with one directory per class:

```text
lamoda_dataset/
  class_name_1/
    image_001.jpg
  class_name_2/
    image_001.jpg
```

Alternatively, set `CLOTHING_DATASET_DIR` to the dataset directory before starting Jupyter. Drive access permissions and the linked dataset contents have not been verified.

The notebook keeps categories with at least 20 images and creates a seeded 70/15/15 train/validation/test split. The previously included data had 1,748 images in 18 eligible classes and one unreadable image; the loader substitutes a gray image for unreadable files. Inspect your downloaded data before training.

## Train and evaluate

Open `clothes_classification.ipynb` with the repository root as the working directory and run cells in order. No Google Colab or Drive mount is required. The default run trains for 30 epochs; adjust the training settings in the notebook as needed.

Generated checkpoints and plots go to `lamoda_checkpoints/`, which is ignored by Git. Set `CLOTHING_CHECKPOINTS_DIR` to use another output directory. Do not point training output at an irreplaceable checkpoint: a new best validation score overwrites `best_model.pth`.

## Checkpoints

No `.pth` or `.pt` file existed in the repository at inspection. ImageNet weights automatically downloaded by torchvision are the initial pretrained backbone; they are not a trained clothing classifier.

[Supplied best_model.pth on Google Drive](https://drive.google.com/file/d/19FwwZDYOh6xpC1klz0-6YYHU6yYJaBYO/view?usp=sharing)

Place your supplied checkpoint at `best_model.pth` in the repository root. You will add this binary yourself; it is not included or inspected in this commit. Its filename alone does not establish its architecture, labels, accuracy, or whether it is an initial or trained checkpoint.

To use it with the notebook evaluation cell, first initialize the data and model cells, then load `REPO_ROOT / 'best_model.pth'` instead of the generated training checkpoint. Verify its format, architecture, number of classes, and exact class order before evaluation. Do not run the training cell when you only want to evaluate the supplied model.

The notebook saves a dictionary containing `epoch`, `model_state_dict`, `class_names`, `num_classes`, `val_acc`, and `history`. A checkpoint in this format represents a trained model selected by validation accuracy. To evaluate an existing compatible checkpoint, initialize the notebook's data and model cells, then run the evaluation cell using its path instead of training again. Preserve the checkpoint's exact class order; verify it matches the dataset before interpreting predictions. A separately supplied checkpoint may use another format and must be inspected first.

Training currently starts a fresh optimizer/scheduler. A saved best-model file does not contain optimizer or scheduler state, so it does not support exact training resumption without additional code.

## Optional scraper

```bash
python lamoda_scraper_v3_1.py --list-categories
python lamoda_scraper_v3_1.py --output ./lamoda_dataset --max-images 200
```

Live scraping requires Chrome, a compatible WebDriver, and network access to Lamoda and its image hosts. The scraper currently hardcodes `/usr/bin/google-chrome`; this cloud machine instead has `/usr/bin/chromium`. Category listing was verified, but live scraping has not been validated. Scraping is unnecessary when using the linked dataset.

## Validation and remaining work

The environment was verified with CPU model forward/backward, pretrained inference, checkpoint serialization, plotting, dependency checks, and Jupyter execution. Full 30-epoch training was not run. After dataset removal, environment validation uses generated tensors and does not require images.

Still needed: add your supplied checkpoint to the repository root, inspect its format and class labels, verify the Drive download permissions, and validate the model against its matching dataset. Dataset deletion removes working-tree files in the next commit; historical Git commits still contain their original image objects. No Git history rewrite has been performed.
