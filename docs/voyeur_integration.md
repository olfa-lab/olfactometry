# Voyeur integration
This readme encompasses how to interface the olfactometry suite with the Rinberg lab's "Voyeur" program. This has been
designed with the utmost in convenience in mind, and this software suite will actually generate template code for you
to use within your Voyeur protocol.

## Generating and using stimulus dictionaries.
To use the olfactometry suite, you need to give it information to open vials, change flows, and modify dilutors. This
is easy using the *Stimulus Dictionary* interface. This dictionary structure depends on the configuration of our
olfactometer. Luckily there is a template generator:

1. First, open the olfactometry program:
    ```python
    >>> import olfactometry
    >>> olfactometry.main()
    ```

2. Next go to Tools:Stimulus Template...
3. A dialog box should appear with a dictionary template that looks something like this:
    ```python
    {'olfas': {'olfa_0': {'dilutors': {'dilutor_0': {'air_flow': 'int flowrate in flow units',
                                                     'dilution_factor': 'float (optional)',
                                                     'vac_flow': 'int flowrate in flow units'}},
                          'mfc_0_flow': 'numeric flowrate',
                          'mfc_1_flow': 'numeric flowrate',
                          'odor': 'str (odorname) or int (vialnumber).',
                          'vialconc': 'float concentration of odor to be presented (optional if using vialnumber)'}}}
    ```
4. Copy and paste this template dictionary into your code and modify it with the values you wish to use for your stimulus.
5. Now, to set these stimulus parameters, do the following:
    ```python
    import olfactometry
    olfas = olfactometry.Olfactometers()
    odor =    {'olfas': {'olfa_0': {'dilutors': {'dilutor_0': {'air_flow': 900,
                                                               'dilution_factor': 0.1,
                                                               'vac_flow': 900}},
                                    'mfc_0:flow': 900,
                                    'mfc_1:flow': 100,
                                    'odor': 'pinene',
                                    'vialconc': 0.01}}}
    success = olfas.set_stimulus(odor)  # returns True if setting was completed.
    ```
6. Usually, you will use a "currentstim" object. When you generate your stimulus dictionary, just add it to your
stimulus as you generate it:

    ```python
    import olfactometry
    from Stimulus import OdorStimulus
    olfas = olfactometry.Olfactometers()

    odor =    {'olfas': {'olfa_0': {'dilutors': {'dilutor_0': {'air_flow': 900,
                                                               'dilution_factor': 0.1,
                                                               'vac_flow': 900}},
                                    'mfc_0_flow': 900,
                                    'mfc_1_flow': 100,
                                    'odor': 'pinene',
                                    'vialconc': 0.01}}}
    stim = OdorStim(olfa_stim_dict=odor, ...)  # this can be LaserStimulus or LaserTrainStimulus too
    ```

    To retrieve and set this (probably in your trial_parameters method):

    ```python
    odor_dict = stim.olfa_stim_dict
    success = olfas.set_stimulus(odor_dict)
    ```

7. When your trial is completed, you have to close your vials. This usually happens in the "end_of_trial" method. To
close the vials by calling the following method in your Olfactometers object:

    ```python
    olfas.set_dummy_vials()  # Iterates through all olfactometers and closes all the vials.
    ```

## Saving your stimuli.
This software suite will also generate templates for saving your files in the Voyeur table. These templates can be
generated within voyeur and simply added to your protocol_parameters dictionary that is saved.

To do this, we must modify our Voyeur protocol:

First, add the following call to your olfactometers' template generator to your protocol_parameters method:

```python
import olfactometry

class MyProtocol(Protocol):
    def __init__(self):
        self.olfactometers = olfactometry.Olfactometers()

    def protocol_parameters(self):
        """this defines the table and is called on the start of the first trial."""
        params_def = {"mouse"         : db.String32,
                      "rig"           : db.String32,
                      "session"       : db.Int, ...
                      }
        olfa_params_dict = self.olfactometers.generate_tables_definition()
        params_def.update(olfa_params_dict)  # this adds the olfa dict to the main dictionary.
        return params_def
```

The above code generates the table that you are saving data to when the first trial is called. To save individual trial
information, use the following code in your trial_parameters method:

```python
    def trial_parameters(self):
        """this is called for every trial and returns a protocol and controller dictionary of trial parameters"""
        protocol_params = {"mouse"         : self.mouse,
                           "rig"           : self.rig,
                           "session"       : self.session, ...
                           }
        olfa_stim_dict = self.currentstim.olfa_stim_dict
        olfa_stim_flat = olfactometry.flatten_dictionary(olfa_stim_dict)  # this flattens the dictionary for saving.
        protocol_params.update(olfa_stim_flat)

        return protocol_params
```

Obviously, there is much more going on in both of the above Voyeur methods. These are simply minimal examples to illustrate use
of this functionality.