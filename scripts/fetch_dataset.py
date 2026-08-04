import argparse
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", default="118e4bd")
    parser.add_argument("--destination", type=Path, default=Path("vendor/exercises-dataset"))
    args = parser.parse_args()
    url = f"https://github.com/hasaneyldrm/exercises-dataset/archive/{args.revision}.tar.gz"
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / "dataset.tar.gz"
        with urlopen(url, timeout=120) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with tarfile.open(archive) as tar:
            tar.extractall(temp, filter="data")
        extracted = next(Path(temp).glob("exercises-dataset-*"))
        if args.destination.exists():
            shutil.rmtree(args.destination)
        shutil.copytree(extracted, args.destination)
    print(f"Dataset {args.revision} downloaded to {args.destination}")


if __name__ == "__main__":
    main()
