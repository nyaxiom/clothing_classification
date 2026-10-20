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

## Checkpoint

The trained model checkpoint is included as [`best_model.pth`](best_model.pth) in the repository root and stored with Git LFS. After cloning, download the model weights with:

```bash
git lfs install
git lfs pull
```

To evaluate it, initialize the notebook's data and model cells, then change the checkpoint path in the evaluation cell to `REPO_ROOT / 'best_model.pth'`. Skip the training cell and ensure the dataset's class order matches the checkpoint's `class_names`.

New training runs save their best checkpoint separately in `lamoda_checkpoints/`. The notebook saves model weights and training metrics, but not optimizer or scheduler state for exact training resumption.

## Optional scraper

```bash
python lamoda_scraper_v3_1.py --list-categories
python lamoda_scraper_v3_1.py --output ./lamoda_dataset --max-images 200
```

Live scraping requires Chrome, a compatible WebDriver, and network access to Lamoda and its image hosts. The scraper currently hardcodes `/usr/bin/google-chrome`; this cloud machine instead has `/usr/bin/chromium`. Category listing was verified, but live scraping has not been validated. Scraping is unnecessary when using the linked dataset.

## Validation and remaining work

The environment was verified with CPU model forward/backward, pretrained inference, checkpoint serialization, plotting, dependency checks, and Jupyter execution. Full 30-epoch training was not run. After dataset removal, environment validation uses generated tensors and does not require images.

The uploaded checkpoint has not yet been validated against the external dataset. Historical Git commits still contain the removed dataset images; no Git history rewrite has been performed.
