#!/usr/bin/env python3
"""
Парсер Lamoda.ru
"""
 
import os
import sys
import json
import csv
import time
import hashlib
import re
import logging
from pathlib import Path
 
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
 
import requests as req
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
 
try:
    from tqdm.notebook import tqdm
except ImportError:
    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lamoda")
 
# ---------------------------------------------------------------------------
# 18 категорий
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    "блузы_и_рубашки": [
        "/c/399/clothes-bluzy-rubashki/",
        "/c/515/clothes-muzhskie-rubashki-i-sorochki/",
    ],
    "боди": [
        "/c/4418/clothes-body/",
    ],
    "брюки": [
        "/c/401/clothes-bryuki-shorty-kombinezony/",
        "/c/517/clothes-muzhskie-bryuki/",
    ],
    "верхняя_одежда": [
        "/c/357/clothes-verkhnyaya-odezhda/",
        "/c/479/clothes-muzhskaya-verkhnyaya-odezhda/",
    ],
    "джемперы_свитеры_кардиганы": [
        "/c/371/clothes-trikotazh/",
        "/c/497/clothes-muzhskoy-trikotazh/",
    ],
    "джинсы": [
        "/c/397/clothes-d-insy/",
        "/c/513/clothes-muzhskie-d-insy/",
    ],
    "домашняя_одежда": [
        "/c/4651/clothes-dom-odejda/",
        "/c/5289/clothes-odezhdadlyadomamuj/",
    ],
    "комбинезоны": [
        "/c/4184/clothes-coveralls/",
        "/c/7660/clothes-men-kombenizony/",
    ],
    "купальники": [
        "/c/3002/clothes-kupalniki/",
    ],
    "нижнее_белье": [
        "/c/709/clothes-nizhneye-belyo/",
        "/c/523/clothes-muzhskoe-nizhneye-belyo/",
    ],
    "пиджаки_и_костюмы": [
        "/c/367/clothes-pidzhaki-zhaketi/",
        "/c/3043/clothes-pid-aki-kostumi-muzhskie/",
    ],
    "платья_и_сарафаны": [
        "/c/369/clothes-platiya/",
    ],
    "пляжная_одежда": [
        "/c/5219/clothes-plyazhnayaodezhda/",
    ],
    "спортивные_костюмы": [
        "/c/415/clothes-kostyumy/",
        "/c/3042/clothes-sportivnye-kostyumy-muzhskie/",
    ],
    "топы_и_майки": [
        "/c/2627/clothes-topy/",
        "/c/3039/clothes-topyi-muzhskie/",
    ],
    "футболки_и_поло": [
        "/c/2478/clothes-futbolki/",
        "/c/2512/clothes-muzhskie-futbolki/",
    ],
    "худи_и_свитшоты": [
        "/c/2474/clothes-tolstovki-olimpiyki/",
        "/c/2508/clothes-tolstovki-i-olimpiyki/",
    ],
    "шорты": [
        "/c/2485/clothes-shorty/",
        "/c/519/clothes-muzhskie-shorty/",
    ],
    "юбки": [
        "/c/423/clothes-yubki/",
    ],
}
 
# ---------------------------------------------------------------------------
# Браузер
# ---------------------------------------------------------------------------
def create_driver():
    opts = Options()
    opts.binary_location = "/usr/bin/google-chrome"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver
 
def create_session():
    s = req.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.lamoda.ru/",
    })
    return s
 
# ---------------------------------------------------------------------------
# Парсер
# ---------------------------------------------------------------------------
class LamodaScraper:
    BASE = "https://www.lamoda.ru"
 
    def __init__(self, output_dir="./dataset", max_images=200, delay=3.0):
        self.output_dir = Path(output_dir)
        self.max_images = max_images
        self.delay = delay
        self.driver = None
        self.session = create_session()
        self.seen_hashes = set()
        self.metadata = []
        self.stats = {}
 
    def start(self):
        logger.info("Запуск браузера...")
        self.driver = create_driver()
        logger.info("Готов")
 
    def stop(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
 
    def _scroll(self, pause=2.0, max_scrolls=15):
        last_h = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_h = self.driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h
 
    def _get_products(self):
        """Собирает уникальные товары с картинками со страницы."""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "img"))
            )
        except TimeoutException:
            return []
 
        self._scroll()
 
        products = []
        seen_skus = set()
        seen_imgs = set()
 
        all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
 
        for img in all_imgs:
            try:
                src = (
                    img.get_attribute("src")
                    or img.get_attribute("data-src")
                    or ""
                )
 
                if not src or "data:image" in src or "lmcdn" not in src:
                    continue
 
                if "/adv/" in src or "/banners/" in src:
                    continue
 
                sku_match = re.search(r'/([A-Z0-9]{10,})_', src)
                if not sku_match:
                    continue
 
                sku = sku_match.group(1)
 
                if sku in seen_skus:
                    continue
                seen_skus.add(sku)
 
                src = re.sub(r"/img\d+x\d+/", "/img600x866/", src)
                src = src.split("?")[0]
                src = src.replace("_2x.", ".")
 
                if src in seen_imgs:
                    continue
                seen_imgs.add(src)
 
                products.append({
                    "image_url": src,
                    "sku": sku,
                })
 
            except Exception:
                continue
 
        return products
 
    def _download(self, url, save_path):
        try:
            r = self.session.get(url, timeout=20)
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "")
            if not ct.startswith("image"):
                return False
            content = r.content
            if len(content) < 1000:
                return False
            h = hashlib.md5(content).hexdigest()
            if h in self.seen_hashes:
                return False
            self.seen_hashes.add(h)
            ext = ".png" if "png" in ct else ".webp" if "webp" in ct else ".jpg"
            path = save_path.with_suffix(ext)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(content)
            return True
        except Exception:
            return False
 
    def _already_done(self, name):
        """Проверяет, скачана ли уже категория."""
        cat_dir = self.output_dir / name
        if not cat_dir.exists():
            return False
        image_ext = {".jpg", ".jpeg", ".png", ".webp"}
        count = len([f for f in cat_dir.iterdir() if f.suffix.lower() in image_ext])
        return count >= self.max_images * 0.8
 
    def _scrape_single_url(self, url_path, existing_skus, remaining):
        """Парсит один URL каталога, возвращает список новых товаров."""
        products = []
        page = 1
        max_pages = (remaining // 30) + 5
 
        while page <= max_pages and len(products) < remaining:
            sep = "&" if "?" in url_path else "?"
            url = f"{self.BASE}{url_path}{sep}page={page}"
            logger.info(f"  Стр. {page}...")
 
            try:
                self.driver.get(url)
                time.sleep(self.delay)
                page_products = self._get_products()
 
                if not page_products:
                    logger.info(f"  Пусто на стр. {page}")
                    break
 
                # Фильтруем дубли
                new = [p for p in page_products
                       if p["sku"] not in existing_skus]
                if not new:
                    logger.info(f"  Нет новых товаров")
                    break
 
                for p in new:
                    existing_skus.add(p["sku"])
                products.extend(new)
                logger.info(f"  +{len(new)} товаров")
 
            except Exception as e:
                logger.warning(f"  Ошибка: {e}")
                break
 
            page += 1
            time.sleep(self.delay)
 
        return products
 
    def scrape_category(self, name, url_list):
        """Парсит категорию из нескольких URL в одну папку."""
        if self._already_done(name):
            cat_dir = self.output_dir / name
            image_ext = {".jpg", ".jpeg", ".png", ".webp"}
            count = len([f for f in cat_dir.iterdir() if f.suffix.lower() in image_ext])
            logger.info(f"\n>> {name}: уже скачано ({count} шт.), пропускаем")
            self.stats[name] = count
            return count
 
        logger.info(f"\n>> {name} ({len(url_list)} URL)")
 
        cat_dir = self.output_dir / name
        cat_dir.mkdir(parents=True, exist_ok=True)
 
        all_products = []
        existing_skus = set()
 
        # Парсим каждый URL по очереди
        for i, url_path in enumerate(url_list):
            remaining = self.max_images - len(all_products)
            if remaining <= 0:
                break
 
            logger.info(f"  URL {i+1}/{len(url_list)}: {url_path}")
            new_products = self._scrape_single_url(url_path, existing_skus, remaining)
            all_products.extend(new_products)
            logger.info(f"  Итого для категории: {len(all_products)}")
 
        # Скачиваем
        all_products = all_products[:self.max_images]
        downloaded = 0
 
        items = list(enumerate(all_products))
        if tqdm:
            items = tqdm(items, desc=f"  Скачивание {name}", unit="img")
 
        for idx, prod in items:
            path = cat_dir / f"{name}_{idx+1:05d}"
            if self._download(prod["image_url"], path):
                downloaded += 1
                self.metadata.append({
                    "filepath": str(path),
                    "category": name,
                    "source_url": prod["image_url"],
                    "sku": prod["sku"],
                })
            time.sleep(0.2)
 
        self.stats[name] = downloaded
        logger.info(f"  Скачано: {downloaded} изображений")
        return downloaded
 
    def save_metadata(self):
        csv_path = self.output_dir / "metadata.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["filepath", "category", "source_url", "sku"])
            w.writeheader()
            w.writerows(self.metadata)
 
        stats_path = self.output_dir / "category_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_images": sum(self.stats.values()),
                "total_categories": len(self.stats),
                "categories": self.stats,
            }, f, ensure_ascii=False, indent=2)
 
        logger.info(f"\nМетаданные: {csv_path}")
        logger.info(f"Статистика: {stats_path}")
 
    def run(self, categories=None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
 
        if categories:
            selected = {}
            for cat in categories:
                for k, v in CATEGORY_MAP.items():
                    if cat.lower() in k.lower():
                        selected[k] = v
            if not selected:
                logger.error(f"Категории не найдены: {categories}")
                return
        else:
            selected = CATEGORY_MAP
 
        logger.info(f"Парсим {len(selected)} категорий, макс. {self.max_images} фото/кат.")
 
        self.start()
        try:
            total = 0
            for name, url_list in selected.items():
                total += self.scrape_category(name, url_list)
                time.sleep(self.delay)
            self.save_metadata()
 
            print("\n" + "=" * 60)
            print(f"Готово! {total} изображений, {len(self.stats)} категорий")
            print("=" * 60)
            for cat, cnt in self.stats.items():
                print(f"  {cat:35s} {cnt:5d}")
        finally:
            self.stop()
 
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", "-o", default="./dataset")
    p.add_argument("--max-images", "-n", type=int, default=200)
    p.add_argument("--delay", "-d", type=float, default=3.0)
    p.add_argument("--categories", "-c", nargs="+", default=None)
    p.add_argument("--list-categories", action="store_true")
    args = p.parse_args()
 
    if args.list_categories:
        for i, name in enumerate(CATEGORY_MAP, 1):
            print(f"  {i:2d}. {name}")
        sys.exit(0)
 
    s = LamodaScraper(args.output, args.max_images, args.delay)
    s.run(args.categories)