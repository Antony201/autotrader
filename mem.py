import asyncio
import logging
import resource
import tracemalloc
import ujson
from datetime import datetime as dt
from pathlib import Path

from pympler import muppy, summary

import settings

logger = logging.getLogger('memwatcher')


def ts():
    return dt.now()


def get_usage() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


async def mem_watcher_pympler():
    Path('./_mem_reports/pympler').mkdir(parents=True, exist_ok=True)
    while True:
        print_report_pympler()
        await asyncio.sleep(settings.MEM_CHECK_INTERVAL)


def print_report_pympler():
    TYPE, COUNT, SIZE = range(3)

    all_objects = muppy.get_objects()
    sum1 = summary.summarize(all_objects)
    with open(f'_mem_reports/pympler/{ts()}.txt', 'w') as f:
        for line in sorted(sum1, key=lambda x: x[SIZE], reverse=True)[:settings.MEM_OBJECTS_COUNT_LIMIT]:
            f.write(f'{line[TYPE]:>100}\'> {line[COUNT]:>30}{summary.stringutils.pp(line[SIZE]):>15}\n')


async def mem_watcher_tracemalloc():
    Path('./_mem_reports/tracemalloc').mkdir(parents=True, exist_ok=True)
    while True:
        print_report_tracemalloc()
        await asyncio.sleep(settings.MEM_CHECK_INTERVAL)


def print_report_tracemalloc():
    tracemalloc.start()

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')

    result = []
    for stat in top_stats[:100]:
        result.append(str(stat))

    with open(f'_mem_reports/tracemalloc/{ts()}.json', 'w') as f:
        ujson.dump(result, f)
