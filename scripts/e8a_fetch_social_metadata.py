"""Bounded author-dataset read. Retain only timing/ticker/hash metadata, never posts.

Connector metadata identified fixed blobs; its size limit prevents CSV transfer.
No platform credentials, paid APIs, live feeds, model inference or training.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import time
import os
import urllib.request
from pathlib import Path
from e8a_core import dump, digest, write_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('E8A_OUTPUT', ROOT / 'outputs/e8a_20261108')).resolve()
REV = 'eb8390f4a0e7f3c51913d22173c30905b15e8bca'
BLOBS = {
 'processed_stockemo.csv': '42a5afe66ebbaf62f648c2d2c495caa2033646dd',
 'train_stockemo.csv': 'f6bd06912bca59823841908bc8fab024bf3c36a9',
 'val_stockemo.csv': '4fd30e2cc0a4165dfc85e6242250328b6924f4c3',
 'test_stockemo.csv': '54b3a79d66ca9c4836368c31c7e7bfe88aed3e74'
}

def main():
    if (OUT / 'inputs/social_metadata.csv').exists():
        raise FileExistsError('Preserve first acquisition; no implicit refresh')
    metadata, manifest = [], []
    for filename, blob in BLOBS.items():
        url = f'https://raw.githubusercontent.com/adlnlp/StockEmotions/{REV}/tweet/{filename}'
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                payload = response.read(20_000_001)
                if len(payload) > 20_000_000:
                    raise ValueError('Size limit exceeded')
                status = response.status
            observed = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
            if observed != blob:
                raise ValueError('Author Git blob mismatch')
            reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
            count, skipped = 0, 0
            for i, row in enumerate(reader):
                count += 1
                # Generic aliases are fixed before reading any prediction outcomes.
                date = next((row[k] for k in ('date', 'Date', 'created_at', 'timestamp') if row.get(k)), '')
                ticker = next((row[k] for k in ('ticker', 'Ticker', 'symbol') if row.get(k)), '')
                if ticker not in ('AAPL', 'TSLA'):
                    continue
                if not ('2012-01-01' <= date[:10] <= '2025-12-31'):
                    skipped += 1; continue
                content = next((row[k] for k in ('original', 'text', 'content', 'processed') if row.get(k)), '')
                metadata.append({'dataset': 'StockEmotions', 'view': filename,
                                 'source_row': i + 1, 'ticker': ticker, 'date_raw': date,
                                 'record_id_hash': digest(row.get('id', str(i))),
                                 'text_hash': digest(content) if content else '',
                                 'original_created_at_certified': False,
                                 'historical_version_certified': False,
                                 'historical_first_seen': '', 'retrieved_utc': now})
            manifest.append({'url': url, 'revision': REV, 'git_blob_sha1': observed,
                             'response_sha256': hashlib.sha256(payload).hexdigest(),
                             'bytes_read': len(payload), 'status': status, 'retrieved_utc': now,
                             'all_file_rows': count, 'columns': reader.fieldnames,
                             'out_of_scope_target_rows_not_inspected': skipped,
                             'raw_content_retained': False,
                             'license_note': 'Author repository access is not certification of platform content redistribution rights'})
            print(filename, count, 'rows; columns:', reader.fieldnames)
        except Exception as exc:
            manifest.append({'url': url, 'retrieved_utc': now, 'status': 'FAILED', 'error': str(exc)})
            print(filename, type(exc).__name__, str(exc))
            break
        time.sleep(1)
    if metadata:
        write_csv(OUT / 'inputs/social_metadata.csv', metadata)
    dump(OUT / 'sources/StockEmotions_acquisition.json', manifest)
    print('Target metadata rows:', len(metadata), '(views overlap; not independent posts)')

if __name__ == '__main__':
    main()
