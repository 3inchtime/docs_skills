"""Export a date range from the bundled synthetic report register."""
import argparse
import csv
from datetime import date
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", type=date.fromisoformat, help="First report date (YYYY-MM-DD)")
    parser.add_argument("end", type=date.fromisoformat, help="Last report date (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("开始日期晚于结束日期")

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["date", "report_id"])
    with Path(__file__).with_name("reports.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if args.start <= date.fromisoformat(row["date"]) <= args.end:
                writer.writerow([row["date"], row["report_id"]])


if __name__ == "__main__":
    main()
