from traits.api import HasTraits, Directory, Bool
import traits.api as traits
from ....base import MetaWorkflow, load_config, register_workflow
from wip_diffusion import config as pconfig

"""
Part 1: MetaWorkflow
"""
mwf = MetaWorkflow()
mwf.help = """
Diffusion tracking workflow
===========================

"""
mwf.uuid = 'fda82554a43511e1b507001e4fb1404c'
mwf.tags = ['diffusion','dti','tracking']
mwf.script_dir = 'fmri'

"""
Part 2: Config
"""

class config(HasTraits):
    uuid = traits.Str(desc="UUID")
    desc = traits.Str(desc='Workflow description')
    # Directories
    working_dir = Directory(mandatory=True, desc="Location of the Nipype working directory")
    sink_dir = Directory(mandatory=True, desc="Location where the BIP will store the results")
    crash_dir = Directory(mandatory=False, desc="Location to store crash files")

    # Execution

    run_using_plugin = Bool(False, usedefault=True, desc="True to run pipeline with plugin, False to run serially")
    plugin = traits.Enum("PBS", "PBSGraph","MultiProc", "SGE", "Condor",
        usedefault=True,
        desc="plugin to use, if run_using_plugin=True")
    plugin_args = traits.Dict({"qsub_args": "-q many"},
        usedefault=True, desc='Plugin arguments.')
    test_mode = Bool(False, mandatory=False, usedefault=True,
        desc='Affects whether where and if the workflow keeps its \
                            intermediary files. True to keep intermediary files. ')
    # Subjects

    subjects= traits.List(traits.Str, mandatory=True, usedefault=True,
        desc="Subject id's. Note: These MUST match the subject id's in the \
                                Freesurfer directory. For simplicity, the subject id's should \
                                also match with the location of individual functional files.")
    # Preprocessing info
    preproc_config = traits.File(desc="preproc json file")

    #Advanced
    use_advanced_options = traits.Bool()
    advanced_script = traits.Code()
    save_script_only = traits.Bool(False)

def create_config():
    c = config()
    c.uuid = mwf.uuid
    c.desc = mwf.help
    return c

mwf.config_ui = create_config

"""
Part 3: View
"""

def create_view():
    from traitsui.api import View, Item, Group, CSVListEditor
    from traitsui.menu import OKButton, CancelButton
    view = View(Group(Item(name='uuid', style='readonly'),
        Item(name='desc', style='readonly'),
        label='Description', show_border=True),
        Group(Item(name='working_dir'),
            Item(name='sink_dir'),
            Item(name='crash_dir'),
            label='Directories', show_border=True),
        Group(Item(name='run_using_plugin'),
            Item(name='plugin', enabled_when="run_using_plugin"),
            Item(name='plugin_args', enabled_when="run_using_plugin"),
            Item(name='test_mode'),
            label='Execution Options', show_border=True),
        Group(Item(name='subjects', editor=CSVListEditor()),
            label='Subjects', show_border=True),
        Group(Item(name='preproc_config'),
            label='Track', show_border=True),
        Group(Item("use_advanced_options"),
            Item("advanced_script"),
            label="Advanced",show_border=True),
        buttons = [OKButton, CancelButton],
        resizable=True,
        width=1050)
    return view

mwf.config_view = create_view

"""
Part 4: Construct Workflow
"""

from ..scripts.diffusion_base import create_workflow

def get_dataflow(c):
    import nipype.pipeline.engine as pe
    import nipype.interfaces.io as nio
    datasource = pe.Node(interface=nio.DataGrabber(infields=['subject_id'],
        outfields=['dwi','mask','bvecs','bvals',"reg","mean"]),
        name='datasource')
    # create a node to obtain the functional images
    datasource.inputs.base_directory = c.sink_dir
    datasource.inputs.template ='*'
    datasource.inputs.field_template = dict(dwi='%s/preproc/outputs/dwi/*',
        mask='%s/preproc/outputs/mask/*', bvecs='%s/preproc/outputs/bvecs/*',
        bvals='%s/preproc/outputs/bvals/*',reg='%s/preproc/outputs/bbreg/*.dat',
        mean='%s/preproc/outputs/mean/*.nii*')
    datasource.inputs.template_args = dict(dwi=[['subject_id']],
        mask=[['subject_id']],
        bvecs=[['subject_id']],
        bvals=[['subject_id']],
        mean=[["subject_id"]],
        reg=[["subject_id"]])
    return datasource

foo = pconfig()

def get_wf(c, prep_c=foo):
    import nipype.pipeline.engine as pe
    import nipype.interfaces.io as nio
    import nipype.interfaces.utility as niu
    workflow = create_workflow()
    datagrabber = get_dataflow(prep_c)
    inputspec = workflow.get_node('inputspec')
    workflow.connect(datagrabber,'mask',inputspec,'mask')
    workflow.connect(datagrabber,'dwi',inputspec,'dwi')
    workflow.connect(datagrabber,'bvecs',inputspec,'bvecs')
    workflow.connect(datagrabber,'bvals',inputspec,'bvals')
    workflow.connect(datagrabber,'reg',inputspec,'reg')
    workflow.connect(datagrabber,'mean',inputspec,'mean')
    workflow.inputs.inputspec.surf_dir=prep_c.surf_dir
    infosource = pe.Node(niu.IdentityInterface(fields=["subject_id"]),name='subject_names')
    workflow.connect(infosource,"subject_id",datagrabber, 'subject_id')
    workflow.connect(infosource,"subject_id",inputspec, 'subject_id')
    sinker = pe.Node(nio.DataSink(),name='sinker')
    outputspec=workflow.get_node('outputspec')
    workflow.connect(outputspec,'fdt_paths',sinker,'track.fdt_paths')
    workflow.connect(outputspec,'log',sinker,'track.log')
    workflow.connect(outputspec,'particle_files',sinker,'track.particle_files')
    workflow.connect(outputspec,'targets',sinker,'track.targets')
    workflow.connect(outputspec,'way_total',sinker,'track.way_total')
    sinker.inputs.base_directory=c.sink_dir
    workflow.connect(infosource,"subject_id",sinker,"container")

    if c.test_mode:
        infosource.iterables=("subject_id", [c.subjects[0]])
    else:
        infosource.iterables=("subject_id", c.subjects)
    workflow.base_dir = c.working_dir
    return workflow

mwf.workflow_function = get_wf

"""
Part 5: Main
"""

def main(config_file):
    c = load_config(config_file,config)

    prep_c = load_config(c.preproc_config, pconfig)

    workflow = get_wf(c,prep_c)

    if c.use_advanced_options:
        exec c.advanced_script

    if c.test_mode:
        workflow.write_graph()

    if c.run_using_plugin:
        workflow.run(plugin=c.plugin, plugin_args=c.plugin_args)
    else:
        workflow.run()

    return 1

mwf.workflow_main_function = main

"""
Part 6: Main
"""

register_workflow(mwf)
