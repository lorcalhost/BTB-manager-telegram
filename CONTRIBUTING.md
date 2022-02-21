# Contributing

Contributions are always welcome, no matter how large or small!

## Locales

To create a new localization file, go in the `locales` folder. As the default locale is English, you might want to copy the `en.yml` file to a new file called respectively to the two letters code of country (e.g. Italian locale will be named `it.yml`). Once your locale is created, don't forget to edit the `README.md` in order to add you new locale to the list of existing locale!

If, after some updates of the telegram bot, your locale happens to be updated, you can use the `check_translation_file.py` routine to see which keys are missing in your file. For example, you can try to type 
```console
python3 check_translation_file.py fr.yml
```
in order to see which keys are missing in the French locale. This routine needs an additional dependancy however : 
```console
pip3 install click
```

## Before committing your change

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
