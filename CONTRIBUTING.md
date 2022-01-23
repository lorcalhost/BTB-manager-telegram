# Contributing

Contributions are always welcome, no matter how large or small!

## Locales

To create a new localization file, go in the `locales` folder. As the default locale is english, you might want to copy the `en.json` file to a new file called respectively to the two letters code of country (e.g. italian locale will be named `it.json`). Once your locale is created, don't forget to edit the `README.md` in order to add you new locale to the list of existing locale!

If, after some updates of the telegram bot, your locale happens to be updated, you can use the `check_translation_file.py` routine to see which keys are missing in your file. For example, you can try to type 
```console
python3 check_translation_file.py fr.json
```
in order to see which keys are missing in the French locale. This routine needs an additional dependancy however : 
```console
pip3 install click
```

## Before commiting your changrs

Your code should be formatted using `black` and `isort`. These programs can be installed with pip:

```console
pip3 install black isort
```

To automatically format your code you can use `pre-commit`.

To manually format your code you can run the following commands:

```console
python3 -m black .
python3 -m isort . --settings-path ./.isort.cfg
```
