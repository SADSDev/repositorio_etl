import os
import ssl
import certifi

os.environ["CUDA_VISIBLE_DEVICES"]="-1"
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
os.environ["OMP_NUM_THREADS"]="1"
os.environ["FLAGS_use_mkldnn"]="0"

ssl._create_default_https_context = (
    lambda: ssl.create_default_context(
        cafile=certifi.where()
    )
)


