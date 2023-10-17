import os.path
from pathlib import Path
from unittest.mock import patch
import pytest
from importlib.machinery import SourceFileLoader
import pandas as pd
import subprocess
import re
import shutil

# omniperf = SourceFileLoader("omniperf", "src/omniperf").load_module()
workload_1 = os.path.realpath("workload")
kernel_name_1 = "vecCopy(double*, double*, double*, int, int) [clone .kd]"
app_1 = ["./sample/vcopy", "1048576", "256"]
ALL_CSVS = [
    "SQ_IFETCH_LEVEL.csv",
    "SQ_INST_LEVEL_LDS.csv",
    "SQ_INST_LEVEL_SMEM.csv",
    "SQ_INST_LEVEL_VMEM.csv",
    "SQ_LEVEL_WAVES.csv",
    "pmc_perf.csv",
    "pmc_perf_0.csv",
    "pmc_perf_1.csv",
    "pmc_perf_10.csv",
    "pmc_perf_11.csv",
    "pmc_perf_12.csv",
    "pmc_perf_13.csv",
    "pmc_perf_14.csv",
    "pmc_perf_15.csv",
    "pmc_perf_16.csv",
    "pmc_perf_2.csv",
    "pmc_perf_3.csv",
    "pmc_perf_4.csv",
    "pmc_perf_5.csv",
    "pmc_perf_6.csv",
    "pmc_perf_7.csv",
    "pmc_perf_8.csv",
    "pmc_perf_9.csv",
    "sysinfo.csv",
    "timestamps.csv",
]
ALL_CSVS_MI200 = [
    "SQ_IFETCH_LEVEL.csv",
    "SQ_INST_LEVEL_LDS.csv",
    "SQ_INST_LEVEL_SMEM.csv",
    "SQ_INST_LEVEL_VMEM.csv",
    "SQ_LEVEL_WAVES.csv",
    "pmc_perf.csv",
    "pmc_perf_0.csv",
    "pmc_perf_1.csv",
    "pmc_perf_10.csv",
    "pmc_perf_11.csv",
    "pmc_perf_12.csv",
    "pmc_perf_13.csv",
    "pmc_perf_14.csv",
    "pmc_perf_15.csv",
    "pmc_perf_16.csv",
    "pmc_perf_2.csv",
    "pmc_perf_3.csv",
    "pmc_perf_4.csv",
    "pmc_perf_5.csv",
    "pmc_perf_6.csv",
    "pmc_perf_7.csv",
    "pmc_perf_8.csv",
    "pmc_perf_9.csv",
    "roofline.csv",
    "sysinfo.csv",
    "timestamps.csv",
]

ROOF_ONLY_CSVS = ['pmc_perf.csv', 'pmc_perf_0.csv', 'pmc_perf_1.csv', 'pmc_perf_2.csv', 'roofline.csv', 'sysinfo.csv', 'timestamps.csv']

Baseline_dir = os.path.realpath("Baseline_mi100")
def metric_compare(errors_pd, baseline_df, run_df, threshold = 1):
    #iterate data one row at a time
    for idx_1, idx_2 in zip(baseline_df.index, run_df.index):
        row_1 = baseline_df.iloc[idx_1]
        row_2 = run_df.iloc[idx_2]
        kernel_name=""
        differences={}
        if "KernelName" in row_2.index:
            kernel_name=row_2["KernelName"]
            differences ={}
        
        for pmc_counter in row_2.index:
            if "Ns" in pmc_counter or "id" in pmc_counter or "[" in pmc_counter:
                # print("skipping "+pmc_counter)
                continue
                # assert 0
                
            if not pmc_counter in list(baseline_df.columns):
                print("error: pmc mismatch! "+pmc_counter+" is not in baseline_df")
                continue
            
            data_1 = row_1[pmc_counter]
            data_2 = row_2[pmc_counter]
            if isinstance( data_1, str) and isinstance( data_2, str):
                if data_1 not in  data_2:
                    print(data_2)
            else:
                # relative difference
                if not data_1 == 0:
                    diff = round(100* abs(data_2 - data_1)/data_1,2)
                    if diff > threshold:
                        print("["+pmc_counter+"] diff is :"+str(diff)+"%")
                        if pmc_counter not in differences.keys():
                            print("["+pmc_counter+"] not found in ", list(differences.keys()))
                            differences[pmc_counter] = diff
                        else:
                            # Why are we here?
                            print("Why did we get here?!?!? errors_pd[idx_1]:", list(differences.keys()))
                            differences[pmc_counter].append(diff)
                else:
                    # if 0 show absolute difference
                    diff = round(data_2 - data_1, 2)
                    if diff > threshold:
                        print(idx_1+"["+pmc_counter+"] diff is :"+str(diff,2))
        errors_pd = pd.concat([errors_pd,pd.DataFrame(differences,index=[kernel_name])])
    return errors_pd
            
        
    

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cmd[0] == "rocm-smi" and p.returncode == 8:
        print("ERROR: No GPU detected. Unable to load rocm-smi")
        assert 0
    return p.stdout.decode("ascii")


def gpu_soc():
    rocminfo = str(
        subprocess.run(
            ["rocminfo"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).stdout.decode("ascii")
    )
    rocminfo = rocminfo.split("\n")
    soc_regex = re.compile(r"^\s*Name\s*:\s+ ([a-zA-Z0-9]+)\s*$", re.MULTILINE)
    gpu_id = list(filter(soc_regex.match, rocminfo))[0].split()[1]

    print("gpu_id", gpu_id)
    if gpu_id == "gfx906":
        return "mi50"
    elif gpu_id == "gfx908":
        return "mi100"
    elif gpu_id == "gfx90a":
        return "mi200"
    elif gpu_id == "gfx900":
        return "vega10"
    else:
        print("Invalid SoC")
        assert 0


soc = gpu_soc()


def test_path():
    # if os.path.exists(workload_1):
    #     shutil.rmtree(workload_1)
    # with pytest.raises(SystemExit) as e:
    #     with patch(
    #         "sys.argv",
    #         [
    #             "omniperf",
    #             "profile",
    #             "-n",
    #             "app_1",
    #             "-VVV",
    #             "--path",
    #             workload_1,
    #             "--",
    #         ]
    #         + app_1,
    #     ):
    #         omniperf.main()
    # # assert successful run
    # assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file,index_col=0)
            print("length is: ", len(file_dict[file].index))
            print(file_dict[file])
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)

def test_kernel():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernel",
                kernel_name_1,
                "kernel_name",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS


def test_kernel_summaries():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernel-summaries",
                "vcopy",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS


def test_ipblocks_SQ():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQC():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQC",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(5, "roofline.csv")

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_TA():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "TA",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))

    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(9, "roofline.csv")

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_TD():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "TD",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))

    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_TCP():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "TCP",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))

    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "pmc_perf_9.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(11, "roofline.csv")

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_TCC():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "TCC",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_10.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "pmc_perf_9.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(12, "roofline.csv")

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SPI():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SPI",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))

    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(10, "roofline.csv")

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_CPC():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "CPC",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(7, "roofline.csv")
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_CPF():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "CPF",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs.insert(5, "roofline.csv")
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQ_CPC():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "CPC",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]

    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQ_TA():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "TA",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQ_SPI():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "SPI",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQ_SQC_TCP_CPC():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "SQC",
                "TCP",
                "CPC",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "pmc_perf_9.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_ipblocks_SQ_SPI_TA_TCC_CPF():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--ipblocks",
                "SQ",
                "SPI",
                "TA",
                "TCC",
                "CPF",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)

    print(sorted(list(file_dict.keys())))
    expected_csvs = [
        "SQ_IFETCH_LEVEL.csv",
        "SQ_INST_LEVEL_LDS.csv",
        "SQ_INST_LEVEL_SMEM.csv",
        "SQ_INST_LEVEL_VMEM.csv",
        "SQ_LEVEL_WAVES.csv",
        "pmc_perf.csv",
        "pmc_perf_0.csv",
        "pmc_perf_1.csv",
        "pmc_perf_10.csv",
        "pmc_perf_2.csv",
        "pmc_perf_3.csv",
        "pmc_perf_4.csv",
        "pmc_perf_5.csv",
        "pmc_perf_6.csv",
        "pmc_perf_7.csv",
        "pmc_perf_8.csv",
        "pmc_perf_9.csv",
        "sysinfo.csv",
        "timestamps.csv",
    ]
    if soc == "mi200":
        expected_csvs = [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "roofline.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]
    assert sorted(list(file_dict.keys())) == expected_csvs
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_dispatch_0():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--dispatch",
                "0",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_dispatch_0_1():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--dispatch",
                "0",
                "1",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_dispatch_2():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--dispatch",
                "2",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_0():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "0",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_1():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "1",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_2():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "2",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_3():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "3",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_4():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "4",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_verbose_5():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--kernelVerbose",
                "5",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_join_type_grid():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--join-type",
                "grid",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_join_type_kernel():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--join-type",
                "kernel",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_device_0():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--device",
                "0",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ALL_CSVS_MI200
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_no_roof():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--no-roof",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == [
            "SQ_IFETCH_LEVEL.csv",
            "SQ_INST_LEVEL_LDS.csv",
            "SQ_INST_LEVEL_SMEM.csv",
            "SQ_INST_LEVEL_VMEM.csv",
            "SQ_LEVEL_WAVES.csv",
            "pmc_perf.csv",
            "pmc_perf_0.csv",
            "pmc_perf_1.csv",
            "pmc_perf_10.csv",
            "pmc_perf_11.csv",
            "pmc_perf_12.csv",
            "pmc_perf_13.csv",
            "pmc_perf_14.csv",
            "pmc_perf_15.csv",
            "pmc_perf_16.csv",
            "pmc_perf_2.csv",
            "pmc_perf_3.csv",
            "pmc_perf_4.csv",
            "pmc_perf_5.csv",
            "pmc_perf_6.csv",
            "pmc_perf_7.csv",
            "pmc_perf_8.csv",
            "pmc_perf_9.csv",
            "sysinfo.csv",
            "timestamps.csv",
        ]
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_sort_dispatches():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--sort",
                "dispatches",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_sort_kernels():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--sort",
                "kernels",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_HBM():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "HBM",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_L2():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "L2",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_vL1D():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "vL1D",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_LDS():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "LDS",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_HBM_LDS():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "HBM",
                "LDS",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_vL1D_LDS():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "vL1D",
                "LDS",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return

    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_mem_levels_L2_vL1D_LDS():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--mem-level",
                "L2",
                "vL1D",
                "LDS",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()
    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return
    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
        
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)


def test_kernel_names():
    if os.path.exists(workload_1):
        shutil.rmtree(workload_1)
    with pytest.raises(SystemExit) as e:
        with patch(
            "sys.argv",
            [
                "omniperf",
                "profile",
                "-n",
                "app_1",
                "-VVV",
                "--path",
                workload_1,
                "--roof-only",
                "--kernel-names",
                "--",
            ]
            + app_1,
        ):
            omniperf.main()

    if soc == "mi100":
        # assert that it did not run
        assert e.value.code == 2
        # Do not continue testing
        return
    # assert successful run
    assert e.value.code == 0
    
    files_in_workload = os.listdir(workload_1)

    # Check if csvs have data
    file_dict = {}
    for file in files_in_workload:
        if file.endswith(".csv"):
            file_dict[file] = pd.read_csv(workload_1 + "/" + file)
            assert len(file_dict[file].index)
    if soc == "mi200":
        print(sorted(list(file_dict.keys())))
        assert sorted(list(file_dict.keys())) == ROOF_ONLY_CSVS
    else:
        assert sorted(list(file_dict.keys())) == ALL_CSVS
    
    for file in file_dict.keys():
        if file == "pmc_perf.csv" or "SQ" in file:
            print(file)
            # read file in Baseline
            df_1  = pd.read_csv(Baseline_dir +"/" +file, index_col=0)
            # get corresponding file from current test run
            df_2 = file_dict[file]
            
            errors = metric_compare(pd.DataFrame(), df_1, df_2, 1)
            if not errors.empty:
                if os.path.exists(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv"):
                    error_log =  pd.read_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv")
                    new_error_log = pd.concat([error_log, errors])
                    new_error_log.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)
                else:
                    errors.to_csv(Baseline_dir +"/" + file.split(".")[0] +"_error_log.csv", index = False)