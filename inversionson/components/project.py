"""
A class which includes information regarding inversion
and sets up all the components that are needed inside
the inversion itself.
"""
# from __future__ import absolute_import

import os
import toml
import shutil
from inversionson import InversionsonError, InversionsonWarning
import warnings


from .communicator import Communicator
from .component import Component
from .lasif_comp import LasifComponent
from .multimesh_comp import MultiMeshComponent
from .flow_comp import SalvusFlowComponent
from .mesh_comp import SalvusMeshComponent
from .opt_comp import SalvusOptComponent
from .storyteller import StoryTellerComponent
from .batch_comp import BatchComponent
from .smooth_comp import SalvusSmoothComponent


class ProjectComponent(Component):
    def __init__(self, information_dict: dict):
        """
        Initiate everything to make it work correctly. Make sure that
        a running inversion can be restarted although this is done.
        """
        self.info = information_dict
        self.__comm = Communicator()
        super(ProjectComponent, self).__init__(self.__comm, "project")
        self.simulation_dict = self._read_config_file()
        self.get_inversion_attributes(first=True)
        self.__setup_components()
        self.get_inversion_attributes(first=False)
        self._validate_inversion_project()

    def _read_config_file(self) -> dict:
        """
        Parse the Lasif config file to use it in the inversion.
        I might set this up to just be some parameters in the class

        :return: Simulation dictionary
        :rtype: dict
        """
        with open(
            os.path.join(self.info["lasif_root"], "lasif_config.toml"), "r"
        ) as fh:
            config_dict = toml.load(fh)

        simulation_info = {}
        solver_settings = config_dict["simulation_settings"]
        simulation_info["start_time"] = solver_settings["start_time_in_s"]
        simulation_info["number_of_time_steps"] = int(
            round(
                (
                    solver_settings["end_time_in_s"]
                    - simulation_info["start_time"]
                )
                / solver_settings["time_step_in_s"]
            )
        )
        simulation_info["end_time"] = solver_settings["end_time_in_s"]
        simulation_info["time_step"] = solver_settings["time_step_in_s"]
        simulation_info["min_period"] = solver_settings["minimum_period_in_s"]
        simulation_info["max_period"] = solver_settings["maximum_period_in_s"]
        simulation_info["attenuation"] = config_dict["salvus_settings"][
            "attenuation"
        ]
        simulation_info["ocean_loading"] = config_dict["salvus_settings"][
            "ocean_loading"
        ]
        simulation_info["absorbing_boundaries_length"] = config_dict[
            "salvus_settings"
        ]["absorbing_boundaries_in_km"]

        return simulation_info

    def get_communicator(self):
        return self.__comm

    def _validate_inversion_project(self):
        """
        Make sure everything is correctly set up in order to perform inversion.

        :param info_dict: Information needed
        :type info_dict: dict
        :param simulation_dict: Information regarding simulations
        :type simulation_dict: dict
        """
        import pathlib

        allowed_interp_modes = ["gll_2_gll", "gll_2_exodus", "exodus_2_gll"]
        if "inversion_id" not in self.info.keys():
            raise ValueError("The inversion needs a name, Key: inversion_id")

        if "inversion_path" not in self.info.keys():
            raise InversionsonError(
                "We need a given path for the inversion root directory."
                " Key: inversion_path"
            )

        if "model_interpolation_mode" not in self.info.keys():
            raise InversionsonError(
                "We need information on how you want to interpolate "
                "the model to simulation meshes. "
                "Key: model_interpolation_mode "
            )

        if self.info["model_interpolation_mode"] not in allowed_interp_modes:
            raise InversionsonError(
                f"The allowable model_interpolation_modes are: "
                f" {allowed_interp_modes}"
            )

        if "meshes" not in self.info.keys():
            raise InversionsonError(
                "We need information on which sorts of meshes you use. "
                "Options are multi-mesh or mono-mesh. "
                "Key: meshes"
            )

        if "gradient_interpolation_mode" not in self.info.keys():
            raise InversionsonError(
                "We need information on how you want to interpolate "
                "the model to simulation meshes. "
                "Key: gradient_interpolation_mode "
            )

        if (
            self.info["gradient_interpolation_mode"]
            not in allowed_interp_modes
        ):
            raise InversionsonError(
                f"The allowable model_interpolation_modes are: "
                f" {allowed_interp_modes}"
            )
        if "HPC" not in self.info.keys():
            raise InversionsonError(
                "We need information regarding your computational resources."
                " run create_dummy_info_file.py for an example"
            )

        if "wave_propagation" not in self.info["HPC"].keys():
            raise InversionsonError(
                "We need specific computational info on wave_propagation"
            )

        if "diffusion_equation" not in self.info["HPC"].keys():
            raise InversionsonError(
                "We need specific computational info on diffusion_equation"
            )

        if "site_name" not in self.info["HPC"]["wave_propagation"].keys():
            raise InversionsonError(
                "We need information on the site where jobs are submitted. "
                "Key: HPC.wave_propagation.site_name"
            )

        if "wall_time" not in self.info["HPC"]["wave_propagation"].keys():
            raise InversionsonError(
                "We need information on the site where jobs are submitted. "
                "Key: HPC.wave_propagation.site_name"
            )

        if "ranks" not in self.info["HPC"]["wave_propagation"].keys():
            raise InversionsonError(
                "We need information on the amount of ranks you want to "
                "run your simulations. Key: HPC.wave_propagation.ranks"
            )

        if "site_name" not in self.info["HPC"]["diffusion_equation"].keys():
            raise InversionsonError(
                "We need information on the site where jobs are submitted. "
                "Key: HPC.diffusion_equation.site_name"
            )

        if "wall_time" not in self.info["HPC"]["diffusion_equation"].keys():
            raise InversionsonError(
                "We need information on the site where jobs are submitted. "
                "Key: HPC.diffusion_equation.site_name"
            )

        if "ranks" not in self.info["HPC"]["diffusion_equation"].keys():
            raise InversionsonError(
                "We need information on the amount of ranks you want to "
                "run your simulations. Key: HPC.diffusion_equation.ranks"
            )

        if "inversion_parameters" not in self.info.keys():
            raise InversionsonError(
                "We need information on the parameters you want to invert for."
                " Key: inversion_parameters"
            )

        if "modelling_parameters" not in self.info.keys():
            raise InversionsonError(
                "We need information on the parameters you keep in your mesh "
                "for forward modelling. Key: modelling_parameters"
            )

        if "n_random_events" not in self.info.keys():
            raise InversionsonError(
                "We need information regarding how many events should be "
                "randomly picked when all events have been used. "
                "Key: n_random_events"
            )

        if "min_ctrl_group_size" not in self.info.keys():
            raise InversionsonError(
                "We need information regarding minimum control group size."
                " Key: min_ctrl_group_size"
            )

        if "inversion_mode" not in self.info.keys():
            raise InversionsonError(
                "We need information on inversion mode. mini-batch or normal"
            )

        if self.info["inversion_mode"] not in ["mini-batch", "mono-batch"]:
            raise InversionsonError(
                "Only implemented inversion modes are mini-batch or mono-batch"
            )

        if "meshes" not in self.info.keys():
            raise InversionsonError(
                "We need to know what sorts of meshes you use. "
                "Either mono-mesh for simulation mesh = inversion mesh "
                "or multi-mesh for wavefield adapted meshes. "
                "Key: meshes"
            )

        if self.info["meshes"] not in ["mono-mesh", "multi-mesh"]:
            raise InversionsonError(
                "We only accept 'mono-mesh' or 'multi-mesh'"
            )

        # Smoothing
        if "Smoothing" not in self.info.keys():
            raise InversionsonError(
                "Please specify smoothing parameters in info file. "
                "Key: Smoothing"
            )

        if "smoothing_mode" not in self.info["Smoothing"].keys():
            raise InversionsonError(
                "Please specify smoothing mode under Smoothing in info file. "
                "Key: Smoothing.smoothing_mode"
            )

        if self.info["Smoothing"]["smoothing_mode"] not in [
            "anisotropic",
            "isotropic",
            "none",
        ]:
            raise InversionsonError(
                "Only implemented smoothing modes are 'anisotropic', "
                "'isotropic' and 'none'"
            )
        if not self.info["Smoothing"]["smoothing_mode"] == "none":
            if "smoothing_lengths" not in self.info["Smoothing"].keys():
                raise InversionsonError(
                    "Please specify smoothing lengths under Smoothing in info "
                    "file. Key: Smoothing.smoothing_lengths"
                )

        if self.info["Smoothing"]["smoothing_mode"] == "anisotropic":
            if not isinstance(
                self.info["Smoothing"]["smoothing_lengths"], list
            ):
                raise InversionsonError(
                    "Make sure you input a list as smoothing_lengths if you "
                    "want to smooth anisotropically. List of length 3. "
                    "Order: r, theta, phi."
                )
            if not len(self.info["Smoothing"]["smoothing_lengths"]) == 3:
                raise InversionsonError(
                    "Make sure your smoothing_lengths are a list of length 3."
                    "Order: r, theta, phi."
                )

        if self.info["Smoothing"]["smoothing_mode"] == "isotropic":
            if isinstance(self.info["Smoothing"]["smoothing_lengths"], list):
                if len(self.info["Smoothing"]["smoothing_lengths"]) == 1:
                    self.info["Smoothing"]["smoothing_lengths"] = self.info[
                        "Smoothing"
                    ]["smoothing_lengths"][0]
                else:
                    raise InversionsonError(
                        "If you give a list of isotropic lengths, you can only"
                        " give a list of length one, as all dimensions will "
                        "be smoothed with equally many wavelengths. You can "
                        "also just give a number."
                    )
        if (
            "Meshing" not in self.info.keys()
            and self.info["meshes"] == "multi-mesh"
        ):
            raise InversionsonError(
                "We need some information regarding your meshes. "
                "We need to know how many elements you want per azimuthal "
                "quarter. Key: Meshing"
            )

        if "elements_per_azimuthal_quarter" not in self.info["Meshing"].keys():
            raise InversionsonError(
                "We need to know how many elements you need per azimuthal "
                "quarter. Key: Meshing.elements_per_azimuthal_quarter"
            )

        if not isinstance(
            self.info["Meshing"]["elements_per_azimuthal_quarter"], int
        ):
            raise InversionsonError(
                "Elements per azimuthal quarter need to be an integer."
            )
        # # Salvus Opt
        # if "salvus_opt_dir" not in self.info.keys():
        #     raise InversionsonError(
        #         "Information on salvus_opt_dir is missing from information")
        # else:
        #     folder = pathlib.Path(self.info["salvus_opt_dir"])
        #     if not (folder / "inversion.toml").exists():
        #         raise InversionsonError("Salvus opt inversion not initiated")

        # Salvus Smoother
        # if "salvus_smoother" not in self.info.keys():
        #     raise InversionsonError(
        #         "We need information regarding location of your salvus "
        #         "smoother binary. Key: salvus_smoother")

        # Lasif
        if "lasif_root" not in self.info.keys():
            raise InversionsonError(
                "Information on lasif_project is missing from information. "
                "Key: lasif_root"
            )
        else:
            folder = pathlib.Path(self.info["lasif_root"])
            if not (folder / "lasif_config.toml").exists():
                raise InversionsonError("Lasif project not initialized")

        # Simulation parameters:
        if "end_time" not in self.simulation_dict.keys():
            raise InversionsonError(
                "Information regarding end time of simulation missing"
            )

        if "time_step" not in self.simulation_dict.keys():
            raise InversionsonError(
                "Information regarding time step of simulation missing"
            )

        if "start_time" not in self.simulation_dict.keys():
            raise InversionsonError(
                "Information regarding start time of simulation missing"
            )

        if "inversion_monitoring" not in self.info.keys():
            raise InversionsonError(
                "Information regarding inversion monitoring is missing"
            )
            if (
                self.info["inversion_monitoring"][
                    "iterations_between_validation_checks"
                ]
                != 0
            ):
                if (
                    len(
                        self.info["inversion_monitoring"]["validation_dataset"]
                    )
                    == 0
                ):
                    raise InversionsonError(
                        "You need to specify a validation dataset if you want"
                        " to check it regularly."
                    )

    def __setup_components(self):
        """
        Setup the different components that need to be used in the inversion.
        These are wrappers around the main libraries used in the inversion.
        """
        LasifComponent(communicator=self.comm, component_name="lasif")
        SalvusOptComponent(communicator=self.comm, component_name="salvus_opt")
        MultiMeshComponent(communicator=self.comm, component_name="multi_mesh")
        SalvusFlowComponent(
            communicator=self.comm, component_name="salvus_flow"
        )
        SalvusMeshComponent(
            communicator=self.comm, component_name="salvus_mesher"
        )
        StoryTellerComponent(
            communicator=self.comm, component_name="storyteller"
        )
        BatchComponent(communicator=self.comm, component_name="minibatch")
        SalvusSmoothComponent(
            communicator=self.comm, component_name="smoother"
        )

    def arrange_params(self, parameters: list) -> list:
        """
        Re-arrange list of parameters in order to have
        them conveniently aranged when called upon. This can be an annoying
        problem when working with hdf5 files.
        This method can only handle a few cases. If it doesn't
        recognize the case it will return an unmodified list.
        
        :param parameters: parameters to be arranged
        :type parameters: list
        """
        case_tti_inv = set(["VSV", "VSH", "VPV", "VPH", "RHO"])
        case_tti_mod = set(
            ["VSV", "VSH", "VPV", "VPH", "RHO", "QKAPPA", "QMU", "ETA"]
        )
        case_iso_mod = set(["QKAPPA", "QMU", "VP", "VS", "RHO"])
        case_iso_inv = set(["VP", "VS"])
        case_iso_inv_dens = set(["VP", "VS", "RHO"])

        if set(parameters) == case_tti_inv:
            parameters = ["VPV", "VPH", "VSV", "VSH", "RHO"]
        elif set(parameters) == case_tti_mod:
            parameters = [
                "VPV",
                "VPH",
                "VSV",
                "VSH",
                "RHO",
                "QKAPPA",
                "QMU",
                "ETA",
            ]
        elif set(parameters) == case_iso_inv:
            parameters = ["VP", "VS"]
        elif set(parameters) == case_iso_inv_dens:
            parameters = ["RHO", "VP", "VS"]
        elif set(parameters) == case_iso_mod:
            parameters = ["QKAPPA", "QMU", "RHO", "VP", "VS"]
        else:
            raise InversionsonError(
                f"Parameter list {parameters} not "
                f"a recognized set of parameters"
            )
        return parameters

    def get_inversion_attributes(self, first=False):
        """
        Read crucial components into memory to keep them easily accessible.
        
        :param first: Befor components are set up, defaults to False
        :type first: bool, optional
        """
        # Simulation attributes
        self.time_step = self.simulation_dict["time_step"]
        self.start_time = self.simulation_dict["start_time"]
        self.end_time = self.simulation_dict["end_time"]
        self.min_period = self.simulation_dict["min_period"]
        self.max_period = self.simulation_dict["max_period"]
        self.attenuation = self.simulation_dict["attenuation"]
        self.abs_bound_length = self.simulation_dict[
            "absorbing_boundaries_length"
        ]
        self.absorbing_boundaries = self.info["absorbing_boundaries"]
        self.ocean_loading = self.simulation_dict["ocean_loading"]

        # Inversion attributes
        self.inversion_root = self.info["inversion_path"]
        self.lasif_root = self.info["lasif_root"]
        self.inversion_id = self.info["inversion_id"]
        self.inversion_mode = self.info["inversion_mode"]
        self.meshes = self.info["meshes"]
        if self.meshes == "multi-mesh":
            self.elem_per_quarter = self.info["Meshing"][
                "elements_per_azimuthal_quarter"
            ]
        self.model_interpolation_mode = self.info["model_interpolation_mode"]
        self.gradient_interpolation_mode = self.info[
            "gradient_interpolation_mode"
        ]
        self.cut_source_radius = self.info[
            "cut_source_region_from_gradient_in_km"
        ]
        self.cut_receiver_radius = self.info[
            "cut_receiver_region_from_gradient_in_km"
        ]
        self.clip_gradient = self.info["clip_gradient"]
        self.site_name = self.info["HPC"]["wave_propagation"]["site_name"]
        self.ranks = self.info["HPC"]["wave_propagation"]["ranks"]
        self.wall_time = self.info["HPC"]["wave_propagation"]["wall_time"]
        self.smoothing_site_name = self.info["HPC"]["diffusion_equation"][
            "site_name"
        ]
        self.smoothing_ranks = self.info["HPC"]["diffusion_equation"]["ranks"]
        self.smoothing_wall_time = self.info["HPC"]["diffusion_equation"][
            "wall_time"
        ]
        self.smoothing_mode = self.info["Smoothing"]["smoothing_mode"]
        self.smoothing_lengths = self.info["Smoothing"]["smoothing_lengths"]

        self.initial_batch_size = self.info["initial_batch_size"]
        self.n_random_events_picked = self.info["n_random_events"]
        self.min_ctrl_group_size = self.info["min_ctrl_group_size"]
        self.maximum_grad_divergence_angle = self.info["max_angular_change"]
        self.dropout_probability = self.info["dropout_probability"]
        self.when_to_validate = self.info["inversion_monitoring"][
            "iterations_between_validation_checks"
        ]
        self.validation_dataset = self.info["inversion_monitoring"][
            "validation_dataset"
        ]
        self.test_dataset = self.info["inversion_monitoring"]["test_dataset"]
        if not first:
            self.current_iteration = (
                self.comm.salvus_opt.get_newest_iteration_name()
            )
            print(f"Current Iteration: {self.current_iteration}")
            self.event_quality = toml.load(
                self.comm.storyteller.events_quality_toml
            )
        self.inversion_params = self.arrange_params(
            self.info["inversion_parameters"]
        )
        self.modelling_params = self.arrange_params(
            self.info["modelling_parameters"]
        )

        # Some useful paths
        self.paths = {}
        self.paths["inversion_root"] = self.inversion_root
        self.paths["lasif_root"] = self.lasif_root
        self.paths["salvus_opt"] = os.path.join(
            self.inversion_root, "SALVUS_OPT"
        )
        if not os.path.exists(self.paths["salvus_opt"]):
            raise InversionsonError(
                "Please make a folder for Salvus opt and initialize it in there"
            )

        self.paths["documentation"] = os.path.join(
            self.inversion_root, "DOCUMENTATION"
        )
        if not os.path.exists(self.paths["documentation"]):
            os.makedirs(self.paths["documentation"])
            os.mkdir(os.path.join(self.paths["documentation"], "BACKUP"))

        self.paths["iteration_tomls"] = os.path.join(
            self.paths["documentation"], "ITERATIONS"
        )
        if not os.path.exists(self.paths["iteration_tomls"]):
            os.makedirs(self.paths["iteration_tomls"])
        # self.paths["salvus_smoother"] = self.info["salvus_smoother"]

        self.paths["control_group_toml"] = os.path.join(
            self.paths["documentation"], "control_groups.toml"
        )

    def create_iteration_toml(self, iteration: str):
        """
        Create the toml file for an iteration. This toml file is then updated.
        To create the toml, we need the events and the control group

        :param iteration: Name of iteration
        :type iteration: str
        """
        iteration_toml = os.path.join(
            self.paths["iteration_tomls"], iteration + ".toml"
        )
        validation = False
        if "validation" in iteration:
            validation = True
        if os.path.exists(iteration_toml):
            warnings.warn(
                f"Iteration toml for iteration: {iteration} already exists. backed it up",
                InversionsonWarning,
            )
            backup = os.path.join(
                self.paths["iteration_tomls"], f"backup_{iteration}.toml"
            )
            shutil.copyfile(iteration_toml, backup)

        it_dict = {}
        it_dict["name"] = iteration
        it_dict["events"] = {}

        last_control_group = []
        if iteration != "it0000_model" and not validation:
            ctrl_grps = toml.load(
                self.comm.project.paths["control_group_toml"]
            )
            prev_iter = self.comm.salvus_opt.get_previous_iteration_name()
            last_control_group = ctrl_grps[prev_iter]["new"]

        if not validation:
            it_dict["last_control_group"] = last_control_group
            it_dict["new_control_group"] = []
        f_job_dict = {
            "name": "",
            "submitted": False,
            "retrieved": False,
            "reposts": 0,
        }
        if validation:
            f_job_dict["windows_selected"] = False
        if not validation:
            a_job_dict = {
                "name": "",
                "submitted": False,
                "retrieved": False,
                "reposts": 0,
            }
            s_job_dict = {
                "name": "",
                "submitted": False,
                "retrieved": False,
                "reposts": 0,
            }
        if self.meshes == "multi-mesh":
            f_job_dict["interpolated"] = False
            if not validation:
                a_job_dict["interpolated"] = False
        # for parameter in self.inversion_params:
        #     s_job_dict[parameter] = {
        #         "name": "",
        #         "submitted": False,
        #         "retrieved": False,
        #     }
        for event in self.comm.lasif.list_events(iteration=iteration):
            if validation:
                jobs = {"forward": f_job_dict}
            if self.inversion_mode == "mini-batch":
                if not validation:
                    jobs = {
                        "forward": f_job_dict,
                        "adjoint": a_job_dict,
                        "smoothing": s_job_dict,
                    }
                it_dict["events"][event] = {
                    "job_info": jobs,
                }
            else:
                if not validation:
                    jobs = {"forward": f_job_dict, "adjoint": a_job_dict}
                it_dict["events"][event] = {
                    "job_info": jobs,
                }
            if not validation:
                it_dict["events"][event]["misfit"] = 0.0
                it_dict["events"][event]["usage_updated"] = False
        if self.inversion_mode == "mono-batch" and not validation:
            it_dict["smoothing"] = s_job_dict
        with open(iteration_toml, "w") as fh:
            toml.dump(it_dict, fh)

    def change_attribute(self, attribute: str, new_value):
        """
        Not possible to change attributes from another class.
        This method should take care of it

        :param attribute: Name of attribute
        :type attribute: str
        :param new_value: The new value to assign to the attribute
        :type new_value: whatever the attribure needs
        """
        if isinstance(new_value, str):
            command = f'self.{attribute} = "{new_value}"'
        elif isinstance(new_value, list):
            command = f"self.{attribute} = {new_value}"
        elif isinstance(new_value, bool):
            command = f"self.{attribute} = {new_value}"
        elif isinstance(new_value, dict):
            command = f"self.{attribute} = {new_value}"
        elif isinstance(new_value, float):
            command = f"self.{attribute} = {new_value}"
        elif isinstance(new_value, int):
            command = f"self.{attribute} = {new_value}"
        else:
            raise InversionsonError(
                f"Method not implemented for type {new_value.type}"
            )
        exec(command)

    def update_control_group_toml(self, new=False, first=False):
        """
        A toml file for monitoring which control group is used in each
        iteration.
        Structure: dict[iteration] = {old: [], new: []}
        :param new: Should the new control group be updated?
        :type new: bool, optional
        :param first: Does the toml need to be created?
        :type first: bool, optional
        """
        iteration = self.current_iteration
        print(f"Iteration: {iteration}")
        if first:
            cg_dict = {}
            cg_dict[iteration] = {"old": [], "new": []}
            with open(self.paths["control_group_toml"], "w") as fh:
                toml.dump(cg_dict, fh)
                return
        else:
            cg_dict = toml.load(self.paths["control_group_toml"])
            if not new:
                prev_iter = self.comm.salvus_opt.get_previous_iteration_name()
                cg_dict[iteration] = {}
                cg_dict[iteration]["old"] = cg_dict[prev_iter]["new"]
                if new not in cg_dict[iteration].keys():
                    cg_dict[iteration]["new"] = []
            if new:
                if iteration not in cg_dict.keys():
                    cg_dict[iteration] = {}
                cg_dict[iteration]["new"] = self.new_control_group

        with open(self.paths["control_group_toml"], "w") as fh:
            toml.dump(cg_dict, fh)

    def update_iteration_toml(self, iteration="current", validation=False):
        """
        Use iteration parameters to update iteration toml file

        :param iteration: Name of iteration
        :type iteration: str
        """
        if iteration == "current":
            iteration = self.current_iteration
        if "validation" in iteration:
            validation = True
        if validation and "validation" not in iteration:
            iteration = f"validation_{iteration}"
        iteration_toml = os.path.join(
            self.paths["iteration_tomls"], iteration + ".toml"
        )
        if not os.path.exists(iteration_toml):
            raise InversionsonError(
                f"Iteration toml for iteration: {iteration} does not exists"
            )
        if os.path.exists(self.paths["control_group_toml"]) and not validation:
            control_group_dict = toml.load(self.paths["control_group_toml"])
            control_group_dict = control_group_dict[iteration]
        else:
            control_group_dict = {"old": [], "new": []}
        it_dict = {}
        it_dict["name"] = iteration
        it_dict["events"] = {}
        # I need a way to figure out what the controlgroup is
        # This definitely needs improvement
        if not validation:
            it_dict["last_control_group"] = control_group_dict["old"]
            it_dict["new_control_group"] = control_group_dict["new"]
        for event in self.comm.lasif.list_events(iteration=iteration):
            jobs = {"forward": self.forward_job[event]}
            if not validation:
                jobs["adjoint"] = self.adjoint_job[event]
            if self.inversion_mode == "mini-batch":
                if not validation:
                    jobs["smoothing"] = self.smoothing_job[event]
                it_dict["events"][event] = {
                    "job_info": jobs,
                }
            else:
                it_dict["events"][event] = {
                    "job_info": jobs,
                }
            if not validation:
                it_dict["events"][event]["misfit"] = self.misfits[event]
                it_dict["events"][event]["usage_updated"] = self.updated[event]
        if self.inversion_mode == "mono-batch" and not validation:
            it_dict["smoothing"] == self.smoothing_job

        with open(iteration_toml, "w") as fh:
            toml.dump(it_dict, fh)

    def get_iteration_attributes(self, validation=False):
        """
        Save the attributes of the current iteration into memory

        :param iteration: Name of iteration
        :type iteration: str
        """
        iteration = self.comm.salvus_opt.get_newest_iteration_name()
        if validation:
            iteration = f"validation_{iteration}"
        iteration_toml = os.path.join(
            self.paths["iteration_tomls"], iteration + ".toml"
        )
        if not os.path.exists(iteration_toml):
            raise InversionsonError(
                f"No toml file exists for iteration: {iteration}"
            )

        it_dict = toml.load(iteration_toml)

        self.iteration_name = it_dict["name"]
        self.current_iteration = self.iteration_name
        self.events_in_iteration = list(it_dict["events"].keys())
        if not validation:
            self.old_control_group = it_dict["last_control_group"]
            self.new_control_group = it_dict["new_control_group"]
            self.adjoint_job = {}
            self.smoothing_job = {}
            self.misfits = {}
            self.updated = {}
        self.forward_job = {}

        # Not sure if it's worth it to include station misfits
        for event in self.events_in_iteration:
            if not validation:
                self.updated[event] = it_dict["events"][event]["usage_updated"]
                self.misfits[event] = it_dict["events"][event]["misfit"]

                self.adjoint_job[event] = it_dict["events"][event]["job_info"][
                    "adjoint"
                ]
                if self.inversion_mode == "mini-batch":
                    self.smoothing_job[event] = it_dict["events"][event][
                        "job_info"
                    ]["smoothing"]
            self.forward_job[event] = it_dict["events"][event]["job_info"][
                "forward"
            ]
        if self.inversion_mode == "mono-batch" and not validation:
            self.smoothing_job = it_dict["smoothing"]

    def get_old_iteration_info(self, iteration: str) -> dict:
        """
        For getting information about something else than current iteration

        :param iteration: Name of iteration
        :type iteration: str
        :return: Information regarding that iteration
        :rtype: dict
        """
        iteration_toml = os.path.join(
            self.paths["iteration_tomls"], iteration + ".toml"
        )
        if not os.path.exists(iteration_toml):
            raise InversionsonError(
                f"No toml file exists for iteration: {iteration}"
            )

        with open(iteration_toml, "r") as fh:
            it_dict = toml.load(fh)
        return it_dict
