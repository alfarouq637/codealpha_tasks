
import os
import sys
import hashlib
import shutil
import argparse
import json
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

try:
    from PIL import Image
    import imagehash
    from tqdm import tqdm
except ImportError:
    print("[ERROR] Missing packages. Run:")
    print("  pip install Pillow imagehash tqdm")
    sys.exit(1)


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}
LABEL_EXTENSION = ".txt"          # YOLO label format


# ─────────────────────────────────────────────
#  Utility Functions
# ─────────────────────────────────────────────

def get_md5(filepath: Path) -> str:

    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_phash(filepath: Path) -> imagehash.ImageHash:

    try:
        with Image.open(filepath) as img:
            img = img.convert("RGB")
            return imagehash.phash(img, hash_size=16)
    except Exception as e:
        return None


def get_label_path(img_path: Path) -> Path | None:

    parts = img_path.parts
    

    if "images" in parts:
        idx = parts.index("images")
        label_parts = list(parts)
        label_parts[idx] = "labels"
        label_path = Path(*label_parts).with_suffix(LABEL_EXTENSION)
        if label_path.exists():
            return label_path
    

    sibling = img_path.with_suffix(LABEL_EXTENSION)
    if sibling.exists():
        return sibling
    
    return None


def collect_images(dataset_dir: Path) -> list[Path]:

    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(dataset_dir.rglob(f"*{ext}"))
        images.extend(dataset_dir.rglob(f"*{ext.upper()}"))
    return sorted(set(images))


def make_quarantine_path(img_path: Path, dataset_dir: Path, quarantine_dir: Path) -> Path:

    try:
        rel = img_path.relative_to(dataset_dir)
    except ValueError:
        rel = Path(img_path.name)
    return quarantine_dir / rel


def move_to_quarantine(
    img_path: Path,
    dataset_dir: Path,
    quarantine_dir: Path,
    dry_run: bool = False
) -> dict:

    result = {
        "image": str(img_path),
        "label": None,
        "image_moved": False,
        "label_moved": False,
        "error": None,
    }

    label_path = get_label_path(img_path)
    if label_path:
        result["label"] = str(label_path)

    if dry_run:
        result["image_moved"] = True  # محاكاة
        if label_path:
            result["label_moved"] = True
        return result


    dst_img = make_quarantine_path(img_path, dataset_dir, quarantine_dir)
    dst_img.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(img_path), str(dst_img))
        result["image_moved"] = True
    except Exception as e:
        result["error"] = str(e)
        return result


    if label_path:
        dst_lbl = make_quarantine_path(label_path, dataset_dir, quarantine_dir)
        dst_lbl.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(label_path), str(dst_lbl))
            result["label_moved"] = True
        except Exception as e:
            result["error"] = f"Image moved but label failed: {e}"

    return result


# ─────────────────────────────────────────────
#  Phase 1 — Exact Duplicates (MD5)
# ─────────────────────────────────────────────

def find_exact_duplicates(images: list[Path]) -> dict[str, list[Path]]:

    print("\n" + "═"*60)
    print("  Phase 1: Exact Duplicate Detection (MD5)")
    print("═"*60)

    hash_map = defaultdict(list)
    
    for img_path in tqdm(images, desc="Computing MD5 hashes", unit="img"):
        try:
            h = get_md5(img_path)
            hash_map[h].append(img_path)
        except Exception as e:
            print(f"\n  [WARN] Could not hash {img_path.name}: {e}")


    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    
    total_dupes = sum(len(v) - 1 for v in duplicates.values())
    print(f"\n  ✓ Found {len(duplicates)} duplicate groups")
    print(f"  ✓ Total images to remove: {total_dupes}")
    
    return duplicates


# ─────────────────────────────────────────────
#  Phase 2 — Near Duplicates (Perceptual Hash)
# ─────────────────────────────────────────────

def find_near_duplicates(
    images: list[Path],
    exact_duplicate_paths: set[Path],
    threshold: int = 8
) -> list[tuple[Path, Path, int]]:

    print("\n" + "═"*60)
    print(f"  Phase 2: Near-Duplicate Detection (pHash, threshold={threshold})")
    print("═"*60)


    candidate_images = [img for img in images if img not in exact_duplicate_paths]
    print(f"  Candidates after removing exact duplicates: {len(candidate_images)}")


    phash_map = {}
    for img_path in tqdm(candidate_images, desc="Computing pHashes", unit="img"):
        ph = get_phash(img_path)
        if ph is not None:
            phash_map[img_path] = ph

    print(f"  Successfully hashed: {len(phash_map)} images")
    print(f"  Comparing pairs... (this may take a while for large datasets)")


    paths = list(phash_map.keys())
    near_dupes = []
    
    n = len(paths)
    total_pairs = n * (n - 1) // 2
    
    with tqdm(total=total_pairs, desc="Comparing pairs", unit="pair") as pbar:
        for i in range(n):
            for j in range(i + 1, n):
                dist = phash_map[paths[i]] - phash_map[paths[j]]
                if dist <= threshold:
                    near_dupes.append((paths[i], paths[j], dist))
                pbar.update(1)

    print(f"\n  ✓ Found {len(near_dupes)} near-duplicate pairs")
    return near_dupes


def cluster_near_duplicates(
    near_dupe_pairs: list[tuple[Path, Path, int]]
) -> list[list[Path]]:

    parent = {}
    
    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for img1, img2, _ in near_dupe_pairs:
        union(img1, img2)
    

    groups = defaultdict(list)
    all_imgs = set()
    for img1, img2, _ in near_dupe_pairs:
        all_imgs.add(img1)
        all_imgs.add(img2)
    
    for img in all_imgs:
        root = find(img)
        groups[root].append(img)
    
    return [g for g in groups.values() if len(g) > 1]


# ─────────────────────────────────────────────
#  Strategy: Which image to KEEP
# ─────────────────────────────────────────────

def choose_keeper(group: list[Path]) -> Path:

    return max(group, key=lambda p: p.stat().st_size)


# ─────────────────────────────────────────────
#  Report Generation
# ─────────────────────────────────────────────

def save_report(
    report: dict,
    output_dir: Path,
    dry_run: bool
) -> None:

    mode = "DRY_RUN" if dry_run else "EXECUTED"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON Report
    json_path = output_dir / f"cleaning_report_{timestamp}_{mode}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    # CSV Summary (for easy review)
    csv_path = output_dir / f"removed_images_{timestamp}_{mode}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["type", "removed_image", "kept_image", "label_moved", "distance"])
        
        for entry in report.get("exact_duplicates_removed", []):
            writer.writerow([
                "EXACT",
                entry.get("image", ""),
                entry.get("kept", ""),
                entry.get("label_moved", False),
                0
            ])
        
        for entry in report.get("near_duplicates_removed", []):
            writer.writerow([
                "NEAR",
                entry.get("image", ""),
                entry.get("kept", ""),
                entry.get("label_moved", False),
                entry.get("distance", "")
            ])
    
    print(f"\n  📄 JSON report saved: {json_path.name}")
    print(f"  📄 CSV summary saved: {csv_path.name}")


# ─────────────────────────────────────────────
#  Main Pipeline
# ─────────────────────────────────────────────

def run_cleaner(
    dataset_dir: str,
    similarity_threshold: int = 8,
    dry_run: bool = False,
    skip_near_duplicates: bool = False,
    quarantine_suffix: str = "_quarantine"
) -> None:
    
    dataset_path = Path(dataset_dir).resolve()
    if not dataset_path.exists():
        print(f"[ERROR] Dataset directory not found: {dataset_path.name}")
        sys.exit(1)
    
    quarantine_path = dataset_path.parent / (dataset_path.name + quarantine_suffix)
    
    print("\n" + "█"*60)
    print("  MAD Dataset Cleaner")
    print("█"*60)
    print(f"  Dataset : {dataset_path.name}")
    print(f"  Quarantine: {quarantine_path.name}")
    print(f"  Threshold : {similarity_threshold} (pHash Hamming distance)")
    print(f"  Mode      : {'DRY RUN (no files moved)' if dry_run else '⚠ LIVE (files will be moved)'}")
    print("█"*60)

    if not dry_run:
        confirm = input("\n  ⚠ Files will be MOVED. Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("  Aborted.")
            sys.exit(0)
    

    print("\n  Scanning for images...")
    all_images = collect_images(dataset_path)
    print(f"  Total images found: {len(all_images)}")
    
    if len(all_images) == 0:
        print("[ERROR] No images found in the specified directory.")
        sys.exit(1)

    report = {
        "dataset_dir": str(dataset_path),
        "quarantine_dir": str(quarantine_path),
        "dry_run": dry_run,
        "timestamp": datetime.now().isoformat(),
        "total_images_scanned": len(all_images),
        "similarity_threshold": similarity_threshold,
        "exact_duplicates_removed": [],
        "near_duplicates_removed": [],
        "summary": {}
    }

    exact_duplicate_paths = set()

    # ════════════════════════════════════════════
    # Phase 1: Exact Duplicates
    # ════════════════════════════════════════════
    exact_groups = find_exact_duplicates(all_images)

    exact_removed_count = 0
    for md5_hash, group in exact_groups.items():
        keeper = choose_keeper(group)
        to_remove = [p for p in group if p != keeper]
        
        for img in to_remove:
            exact_duplicate_paths.add(img)
            move_result = move_to_quarantine(img, dataset_path, quarantine_path, dry_run)
            move_result["kept"] = str(keeper)
            move_result["md5"] = md5_hash
            report["exact_duplicates_removed"].append(move_result)
            exact_removed_count += 1

    print(f"\n  ✓ Exact duplicates processed: {exact_removed_count}")

    # ════════════════════════════════════════════
    # Phase 2: Near Duplicates
    # ════════════════════════════════════════════
    near_removed_count = 0
    
    if not skip_near_duplicates:
        near_dupe_pairs = find_near_duplicates(
            all_images,
            exact_duplicate_paths,
            threshold=similarity_threshold
        )
        
        if near_dupe_pairs:
            clusters = cluster_near_duplicates(near_dupe_pairs)
            print(f"\n  Clustered into {len(clusters)} groups")
            

            dist_map = {}
            for img1, img2, dist in near_dupe_pairs:
                dist_map[(img1, img2)] = dist
                dist_map[(img2, img1)] = dist
            
            for cluster in clusters:
                keeper = choose_keeper(cluster)
                to_remove = [p for p in cluster if p != keeper]
                
                for img in to_remove:
                    dist = dist_map.get((keeper, img), dist_map.get((img, keeper), -1))
                    move_result = move_to_quarantine(img, dataset_path, quarantine_path, dry_run)
                    move_result["kept"] = str(keeper)
                    move_result["distance"] = dist
                    report["near_duplicates_removed"].append(move_result)
                    near_removed_count += 1
        
        print(f"  ✓ Near duplicates processed: {near_removed_count}")
    else:
        print("\n  Phase 2 skipped (--skip_near_duplicates flag set)")

    # ════════════════════════════════════════════
    # Summary
    # ════════════════════════════════════════════
    total_removed = exact_removed_count + near_removed_count
    remaining = len(all_images) - total_removed
    
    report["summary"] = {
        "total_scanned": len(all_images),
        "exact_duplicates_removed": exact_removed_count,
        "near_duplicates_removed": near_removed_count,
        "total_removed": total_removed,
        "remaining_images": remaining,
        "reduction_percent": round(total_removed / len(all_images) * 100, 2)
    }

    print("\n" + "═"*60)
    print("  SUMMARY")
    print("═"*60)
    print(f"  Total scanned        : {len(all_images):,}")
    print(f"  Exact duplicates     : {exact_removed_count:,}")
    print(f"  Near duplicates      : {near_removed_count:,}")
    print(f"  Total removed        : {total_removed:,}")
    print(f"  Remaining images     : {remaining:,}")
    print(f"  Dataset reduced by   : {report['summary']['reduction_percent']}%")
    if dry_run:
        print("\n  *** DRY RUN — No files were actually moved ***")
    else:
        print(f"\n  Quarantine folder    : {quarantine_path.name}")
    print("═"*60)


    quarantine_path.mkdir(parents=True, exist_ok=True)
    save_report(report, quarantine_path, dry_run)

    print("\n  ✅ Done!\n")

    if dry_run and total_removed > 0:
        print("  To execute the cleaning, run without --dry_run flag.")
    
    if total_removed > 0 and not dry_run:
        print(f"  To RESTORE all files, move everything from:")
        print(f"    {quarantine_path.name}")
        print(f"  back to:")
        print(f"    {dataset_path.name}")


# ─────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MAD Dataset Cleaner — Remove exact and near-duplicate images from YOLO dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview only (no files moved):
  python mad_dataset_cleaner.py --dataset_dir "E:/dataset" --dry_run

  # Run with default threshold (8):
  python mad_dataset_cleaner.py --dataset_dir "E:/dataset"

  # Stricter similarity (only very close matches):
  python mad_dataset_cleaner.py --dataset_dir "E:/dataset" --similarity_threshold 5

  # Only exact duplicates, skip near-duplicate detection:
  python mad_dataset_cleaner.py --dataset_dir "E:/dataset" --skip_near_duplicates

Threshold guide:
  0  = identical images (same as MD5, but slower)
  5  = extremely similar (minor compression artifacts only)
  8  = very similar (recommended for dataset cleaning)
  12 = similar but some variation allowed
  15 = loosely similar (may catch different but related images)
        """
    )

    parser.add_argument(
        "--dataset_dir",
        type=str,
        required=True,
        help="Path to the root dataset directory (contains train/valid/test subfolders)"
    )
    parser.add_argument(
        "--similarity_threshold",
        type=int,
        default=8,
        help="Perceptual hash Hamming distance threshold for near-duplicates (default: 8)"
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Preview what would be removed without actually moving any files"
    )
    parser.add_argument(
        "--skip_near_duplicates",
        action="store_true",
        help="Only remove exact duplicates, skip near-duplicate detection (faster)"
    )
    parser.add_argument(
        "--quarantine_suffix",
        type=str,
        default="_quarantine",
        help="Suffix added to dataset folder name to create quarantine folder (default: _quarantine)"
    )

    args = parser.parse_args()

    run_cleaner(
        dataset_dir=args.dataset_dir,
        similarity_threshold=args.similarity_threshold,
        dry_run=args.dry_run,
        skip_near_duplicates=args.skip_near_duplicates,
        quarantine_suffix=args.quarantine_suffix
    )


if __name__ == "__main__":
    main()
