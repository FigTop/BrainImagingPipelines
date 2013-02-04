from .base import MetaWorkflow, load_config, register_workflow


"""
Part 1: Define MetaWorkflow
        - help (description)
        - uuid
        - tags
"""

desc = """
Test Freesurfer workflow
=======================================

This workflow just tests freesurfer to make sure that BIPS is working and freesurfer is correctly set up.

The order of steps is as follows:

#. Grab data
#. Freesurfer source
#. Convert brainmask.mgz to brainmask.nii.gz
#. Convert brainmask.nii.gz to brainmask.mgz
#. DataSink 

Click_ for more documentation


.. Click_: ../../interfaces/generated/bips.workflows.workflow4.html
"""

mwf = MetaWorkflow()
mwf.uuid = '4ba509108afb11e18b5e001e4fb1404c'
mwf.tags = ['TEST','Freesurfer']
mwf.help = desc

"""
Part 2: Define the config class & create_config function
        - The config_ui attribute of MetaWorkflow is defined as the create_config function
"""
# Define Config
from .scripts.u0a14c5b5899911e1bca80023dfa375f2.workflow2 import config

def create_config():
    c = config()
    c.uuid = mwf.uuid
    c.desc = mwf.help
    return c

mwf.config_ui = create_config

"""
Part 3: Create a View
        - MetaWorkflow.config_view is a function that returns a View object
        - Make sure the View is organized into Groups
"""

def create_view():
    from traitsui.api import View, Item, Group
    from traitsui.menu import OKButton, CancelButton
    view = View(Group(Item(name='uuid', style='readonly'),
                Item(name='desc', style='readonly'),
                label='Description', show_border=True),
                Group(Item(name='working_dir'),
                    Item(name='sink_dir'),
                    Item(name='crash_dir'),
                    Item(name='surf_dir'),
                    label='Directories',show_border=True),
                Group(Item(name='run_using_plugin',enabled_when='not save_script_only'),Item('save_script_only'),
                    Item(name='plugin',enabled_when="run_on_grid"),
                    Item(name='plugin_args',enabled_when="run_on_grid"),
                    Item(name='test_mode'),
                    label='Execution Options',show_border=True),
                Group(Item(name='subjects'),
                    label='Subjects',show_border=True),
                buttons = [OKButton, CancelButton],
                resizable=True,
                width=1050)
    return view

mwf.config_view = create_view

"""
Part 4: Workflow Construction
        - Write a function that returns the workflow
        - The workflow should take a config object as the first argument
"""

# Define workflow


def test_fs(c,name='test_fs'):
    """Constructs a workflow to test freesurfer.

Inputs
------

inputspec.subject_id : Freesurfer subject id 
inputspec.sd : Freesurfer SUBJECTS_DIR

Outputs
-------

outputspec.outfile : brainmask.mgz

Returns
--------

a nipype workflow
"""
    import nipype.pipeline.engine as pe
    import nipype.interfaces.utility as util
    import nipype.interfaces.io as nio
    import nipype.interfaces.freesurfer as fs
    from nipype.interfaces.io import FreeSurferSource

    workflow = pe.Workflow(name=name)
    
    # Define Nodes
    inputspec = pe.Node(interface=util.IdentityInterface(fields=['subject_id', 'sd']), name='inputspec')

    inputnode = pe.Node(interface=util.IdentityInterface(fields=["subject_id"]),name="subject_names")
    inputnode.iterables = ("subject_id",c.subjects)
    workflow.connect(inputnode,"subject_id",inputspec,"subject_id")

    fssource = pe.Node(interface = FreeSurferSource(),name='fssource')
    
    convert1 = pe.Node(interface=fs.MRIConvert(),name='converter1')
    
    convert2 = pe.Node(interface=fs.MRIConvert(),name='converter2')
    
    convert1.inputs.out_type = 'niigz'
    convert1.inputs.in_type = 'mgz'
    
    convert2.inputs.out_type = 'mgz'
    convert2.inputs.in_type = 'niigz'
    
    outputspec = pe.Node(interface=util.IdentityInterface(fields=['outfile']), name='outputspec')
    
    # Connect Nodes
    workflow.connect(inputspec,'subject_id',fssource,'subject_id')
    workflow.connect(inputspec,'sd',fssource,'subjects_dir')
    
    workflow.connect(fssource, 'brainmask', convert1, 'in_file')
    workflow.connect(convert1, 'out_file', convert2, 'in_file')
    workflow.connect(convert2, 'out_file', outputspec, 'outfile')

    workflow.base_dir = c.working_dir
    workflow.inputs.inputspec.sd = c.surf_dir
    sinker = pe.Node(nio.DataSink(), name='sinker')
    sinker.inputs.base_directory = c.sink_dir
    workflow.connect(inputnode,"subject_id",sinker,"container")
    workflow.connect(outputspec, 'outfile', sinker, 'test_fs.result')
    workflow.config = {'execution' : {'crashdump_dir' : c.crash_dir}}

    return workflow

mwf.workflow_function = test_fs

"""
Part 5: Define the main function
        - In the main function the path to a json file is passed as the only argument
        - The json file is loaded into a config instance, c
        - The workflow function is called with c and runs
"""

def main(config):
    """Runs test freesurfer workflow

Parameters
----------

config : String
         filename of configuration .json file

"""
    c = load_config(config,create_config)
    wk = test_fs(c)

    if c.run_using_plugin:
        wk.run(plugin=c.plugin,plugin_args=c.plugin_args)
    else:
        wk.run()

mwf.workflow_main_function = main

"""
Part 6: Register the Workflow
"""
register_workflow(mwf)
