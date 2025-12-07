from .general import download_and_execute_setup
from .general import download_and_unzip_setup
from .general import download_setup

from .general import copy_execute_setup
from .general import copy_setup
from .general import copy_all_subfiles_setup

try:
    from .bigquery import bigquery_init_setup
except ImportError:
    bigquery_init_setup = None

try:
    from .post_process import plot_process
except ImportError:
    plot_process = None