##############################################################################bl
# MIT License
#
# Copyright (c) 2021 - 2023 Advanced Micro Devices, Inc. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
##############################################################################el

from abc import ABC, abstractmethod
import logging
import os
import sys
import time
from dash import dcc
from utils.utils import mibench, gen_sysinfo, demarcate
from dash import html
import plotly.graph_objects as go
from utils.roofline_calc import calc_ai, constuct_roof
import numpy as np

SYMBOLS = [0, 1, 2, 3, 4, 5, 13, 17, 18, 20]

class Roofline:
    def __init__(self, args):
        self.__args = args
    
    def error(self,message):
        logging.error("")
        logging.error("[ERROR]: " + message)
        logging.error("")
        sys.exit(1)
    def roof_setup(self):
        # set default workload path if not specified
        if self.__args.path == os.path.join(os.getcwd(), 'workloads'):
            self.__args.path = os.path.join(self.__args.path, self.__args.name, self.__args.target)
        # create new directory for roofline if it doesn't exist
        if not os.path.isdir(self.__args.path):
            os.makedirs(self.__args.path)

    # Main methods
    @abstractmethod
    def pre_processing(self):
        self.roof_setup()
        if self.__args.roof_only:
            # check for sysinfo
            logging.info("[roofline] Checking for sysinfo.csv in " + str(self.__args.path))
            sysinfo_path = os.path.join(self.__args.path, "sysinfo.csv")
            if not os.path.isfile(sysinfo_path):
                logging.info("[roofline] sysinfo.csv not found. Generating...")
                gen_sysinfo(self.__args.name, self.__workload_dir, self.__args.ipblocks, self.__args.remaining, self.__args.no_roof)

    @abstractmethod
    def profile(self):
        if self.__args.roof_only:
            # check for roofline benchmark
            logging.info("[roofline] Checking for roofline.csv in " + str(self.__args.path))
            roof_path = os.path.join(self.__args.path, "roofline.csv")
            if not os.path.isfile(roof_path):
                mibench(self.__args)

            # check for profiling data
            logging.info("[roofline] Checking for pmc_perf.csv in " + str(self.__args.path))
            app_path = os.path.join(self.__args.path, "pmc_perf.csv")
            if not os.path.isfile(app_path):
                logging.info("[roofline] pmc_perf.csv not found. Generating...")
                if not self.__args.remaining:
                    self.error("An <app_cmd> is required to run.\nomniperf profile -n test -- <app_cmd>")
                #TODO: Add an equivelent of characterize_app() to run profiling directly out of this module
                
        elif self.__args.no_roof:
            logging.info("[roofline] Skipping roofline.")
        else:
            mibench(self.__args)

    #NB: Currently the post_prossesing() method is the only one being used by omniperf,
    # we include pre_processing() and profile() methods for those who wish to borrow the roofline module        
    @abstractmethod
    def post_processing(self):
        if self.__args.roof_only:
            standalone_roofline(self.__args.path, self.__args.device, self.__args.sort, self.__args.mem_level, self.__args.kernel_names, self.__args.verbose)

def to_int(a):
    if str(type(a)) == "<class 'NoneType'>":
        return np.nan
    else:
        return int(a)

@demarcate
def standalone_roofline(path_to_dir, dev_id, sort_type, targ_mem_level, kernel_names, verbose):
    import pandas as pd
    from collections import OrderedDict

    # Change vL1D to a interpretable str, if required
    if "vL1D" in targ_mem_level:
        targ_mem_level.remove("vL1D")
        targ_mem_level.append("L1")

    app_path = path_to_dir + "/pmc_perf.csv"
    roofline_exists = os.path.isfile(app_path)
    if not roofline_exists:
        logging.error("[roofline] Error: {} does not exist".format(app_path))
        sys.exit(1)
    t_df = OrderedDict()
    t_df["pmc_perf"] = pd.read_csv(app_path)
    empirical_roofline(
        path_to_dir,
        t_df,
        verbose,
        dev_id,  # [Optional] Specify device id to collect roofline info from
        sort_type,  # [Optional] Sort AI by top kernels or dispatches
        targ_mem_level,  # [Optional] Toggle particular level(s) of memory hierarchy
        kernel_names,  # [Optional] Toggle overlay of kernel names in plot
        True,  # [Optional] Generate a standalone roofline analysis
    )

@demarcate
def generate_plot(
    roof_specs, ai_data, targ_mem_level, is_standalone, kernel_names, verbose, fig=None
) -> go.Figure():
    """Create graph object from ai_data (coordinate points) and ceiling_data (peak FLOP and BW) data.
    """
    if fig is None:
        fig = go.Figure()
    plot_mode = "lines+text" if is_standalone else "lines"
    ceiling_data = constuct_roof(roof_specs, targ_mem_level, verbose)
    logging.debug("[roofline] Ceiling data:\n", ceiling_data)

    #######################
    # Plot ceilings
    #######################
    if targ_mem_level == "ALL":
        cache_hierarchy = ["HBM", "L2", "L1", "LDS"]
    else:
        cache_hierarchy = targ_mem_level

    # Plot peak BW ceiling(s)
    for cache_level in cache_hierarchy:
        fig.add_trace(
            go.Scatter(
                x=ceiling_data[cache_level.lower()][0],
                y=ceiling_data[cache_level.lower()][1],
                name="{}-{}".format(cache_level, roof_specs["dtype"]),
                mode=plot_mode,
                hovertemplate="<b>%{text}</b>",
                text=[
                    "{} GB/s".format(to_int(ceiling_data[cache_level.lower()][2])),
                    None
                    if is_standalone
                    else "{} GB/s".format(to_int(ceiling_data[cache_level.lower()][2])),
                ],
                textposition="top right",
            )
        )

    # Plot peak VALU ceiling
    if roof_specs["dtype"] != "FP16" and roof_specs["dtype"] != "I8":
        fig.add_trace(
            go.Scatter(
                x=ceiling_data["valu"][0],
                y=ceiling_data["valu"][1],
                name="Peak VALU-{}".format(roof_specs["dtype"]),
                mode=plot_mode,
                hovertemplate="<b>%{text}</b>",
                text=[
                    None
                    if is_standalone
                    else "{} GFLOP/s".format(to_int(ceiling_data["valu"][2])),
                    "{} GFLOP/s".format(to_int(ceiling_data["valu"][2])),
                ],
                textposition="top left",
            )
        )

    if roof_specs["dtype"] == "FP16":
        pos = "bottom left"
    else:
        pos = "top left"
    # Plot peak MFMA ceiling
    fig.add_trace(
        go.Scatter(
            x=ceiling_data["mfma"][0],
            y=ceiling_data["mfma"][1],
            name="Peak MFMA-{}".format(roof_specs["dtype"]),
            mode=plot_mode,
            hovertemplate="<b>%{text}</b>",
            text=[
                None
                if is_standalone
                else "{} GFLOP/s".format(to_int(ceiling_data["mfma"][2])),
                "{} GFLOP/s".format(to_int(ceiling_data["mfma"][2])),
            ],
            textposition=pos,
        )
    )
    #######################
    # Plot Application AI
    #######################
    if roof_specs["dtype"] != "I8":
        # Plot the arithmetic intensity points for each cache level
        fig.add_trace(
            go.Scatter(
                x=ai_data["ai_l1"][0],
                y=ai_data["ai_l1"][1],
                name="ai_l1",
                mode="markers",
                marker={"color": "#00CC96"},
                marker_symbol=SYMBOLS if kernel_names else None,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=ai_data["ai_l2"][0],
                y=ai_data["ai_l2"][1],
                name="ai_l2",
                mode="markers",
                marker={"color": "#EF553B"},
                marker_symbol=SYMBOLS if kernel_names else None,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=ai_data["ai_hbm"][0],
                y=ai_data["ai_hbm"][1],
                name="ai_hbm",
                mode="markers",
                marker={"color": "#636EFA"},
                marker_symbol=SYMBOLS if kernel_names else None,
            )
        )

    # Set layout
    fig.update_layout(
        xaxis_title="Arithmetic Intensity (FLOPs/Byte)",
        yaxis_title="Performance (GFLOP/sec)",
        hovermode="x unified",
        margin=dict(l=50, r=50, b=50, t=50, pad=4),
    )
    fig.update_xaxes(type="log", autorange=True)
    fig.update_yaxes(type="log", autorange=True)

    return fig

@demarcate
def empirical_roofline(
    path_to_dir,
    ret_df,
    verbose,
    dev_id=None,
    sort_type="kernels",
    targ_mem_level="ALL",
    incl_kernel_names=False,
    is_standalone=False,
):
    """Generate a set of empirical roofline plots given a directory containing required profiling and benchmarking data
    """
    if incl_kernel_names and (not is_standalone):
        logging.error("ERROR: --roof-only is required for --kernel-names")
        sys.exit(1)

    # Set roofline specifications for targeted data types
    fp32_details = {
        "path": path_to_dir,
        "sort": sort_type,
        "device": 0, # hardcode gpu-id (for benchmark data extraction) to device 0
        "dtype": "FP32",
    }
    fp16_details = {
        "path": path_to_dir,
        "sort": sort_type,
        "device": 0, 
        "dtype": "FP16",
    }
    int8_details = {
        "path": path_to_dir, 
        "sort": sort_type,
        "device": 0,
        "dtype": "I8",
    }

    # Create arithmetic intensity data that will populate the roofline model
    logging.debug("[roofline] Path: ", path_to_dir)
    ai_data = calc_ai(sort_type, ret_df, verbose)
    
    logging.debug("[roofline] AI at each mem level:")
    for i in ai_data:
        logging.debug(i, "->", ai_data[i])
    logging.debug("\n")

    # Generate a roofline figure for each data type
    fp32_fig = generate_plot(
        fp32_details, ai_data, targ_mem_level, is_standalone, incl_kernel_names, verbose
    )
    fp16_fig = generate_plot(
        fp16_details, ai_data, targ_mem_level, is_standalone, incl_kernel_names, verbose
    )
    ml_combo_fig = generate_plot(
        int8_details, ai_data, targ_mem_level, is_standalone, incl_kernel_names, verbose, fp16_fig
    )
    # Create a legend and distinct kernel markers. This can be saved, optionally
    legend = go.Figure(
        go.Scatter(
            mode="markers",
            x=[0] * 10,
            y=ai_data["kernelNames"],
            marker_symbol=SYMBOLS,
            marker_size=15,
        )
    )
    legend.update_layout(
        title="Kernel Names and Markers",
        margin=dict(b=0, r=0),
        xaxis_range=[-1, 1],
        xaxis_side="top",
        yaxis_side="right",
        height=400,
        width=1000,
    )
    legend.update_xaxes(dtick=1)
    # Output will be different depending on interaction type:
    # Save PDFs if we're in "standalone roofline" mode, otherwise return HTML to be used in GUI output
    if is_standalone:
        dev_id = "ALL" if dev_id == -1 else str(dev_id)

        fp32_fig.write_image(path_to_dir + "/empirRoof_gpu-{}_fp32.pdf".format(dev_id))
        ml_combo_fig.write_image(
            path_to_dir + "/empirRoof_gpu-{}_int8_fp16.pdf".format(dev_id)
        )
        # only save a legend if kernel_names option is toggled
        if incl_kernel_names:
            legend.write_image(path_to_dir + "/kernelName_legend.pdf")
        time.sleep(1)
        # Re-save to remove loading MathJax pop up
        fp32_fig.write_image(path_to_dir + "/empirRoof_gpu-{}_fp32.pdf".format(dev_id))
        ml_combo_fig.write_image(
            path_to_dir + "/empirRoof_gpu-{}_int8_fp16.pdf".format(dev_id)
        )
        if incl_kernel_names:
            legend.write_image(path_to_dir + "/kernelName_legend.pdf")
        logging.info("[roofline] Empirical Roofline PDFs saved!")
    else:
        return html.Section(
            id="roofline",
            children=[
                html.Div(
                    className="float-container",
                    children=[
                        html.Div(
                            className="float-child",
                            children=[
                                html.H3(
                                    children="Empirical Roofline Analysis (FP32/FP64)"
                                ),
                                dcc.Graph(figure=fp32_fig),
                            ],
                        ),
                        html.Div(
                            className="float-child",
                            children=[
                                html.H3(
                                    children="Empirical Roofline Analysis (FP16/INT8)"
                                ),
                                dcc.Graph(figure=ml_combo_fig),
                            ],
                        ),
                    ],
                )
            ],
        )