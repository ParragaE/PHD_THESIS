#!/bin/bash
set -e
export PYTHONNOUSERSITE=1
export DARSHAN_PATH=/mnt/netapp1/Store_RES/home/res/resd01/resd01epp/Darshan_3_5_0_hdf5_DXT4M
export HDF5_LIB=/opt/cesga/2020/software/MPI/gcc/system/openmpi/4.1.4_ft3/hdf5/1.12.2/lib
export LD_PRELOAD="${DARSHAN_PATH}/RunTime/lib/libdarshan.so:${HDF5_LIB}/libhdf5.so.200:${HDF5_LIB}/libhdf5_hl.so.200"
exec "$@"
