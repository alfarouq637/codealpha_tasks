# Task 3: MAD Dataset Cleaner (Task Automation) 🧹🧠

An advanced Python CLI automation tool designed to optimize Computer Vision datasets (specifically YOLO formats) by detecting and quarantining exact and near-duplicate images.

## 📝 Description
For this automation task, I went beyond basic file manipulation and built a real-world Data Engineering tool. Training Edge-AI models like YOLO requires high-quality data; redundant images slow down training and cause overfitting. This script automates the tedious process of dataset cleaning by mathematically comparing images and safely isolating redundancies along with their corresponding label files.

## ✨ Key Features
* **Exact Duplicate Detection (MD5):** Uses cryptographic hashing to find identically copied files instantly.
* **Near-Duplicate Detection (pHash):** Utilizes Perceptual Hashing (Hamming distance) to detect visually similar images (e.g., slightly cropped or color-shifted).
* **Safe Quarantine System:** Non-destructive approach. It moves duplicate images and their `.txt` YOLO labels to a `_quarantine` folder instead of permanently deleting them.
* **Automated Reporting:** Generates detailed `.json` diagnostic reports and `.csv` summaries of the cleaning session.
* **CLI Interface:** Fully modularized with `argparse` for flexible execution and threshold tuning.

## 🚀 How to Run
1. Open your terminal.
2. Run the script pointing to your dataset directory:
   ```bash
   python mad_dataset_cleaner.py --dataset_dir "path/to/your/dataset"
3. Options: Use --dry_run to preview changes without moving files, or --similarity_threshold 5 for stricter near-duplicate detection.
