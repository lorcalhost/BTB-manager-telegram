# Custom scripts setup

Users can setup custom bash scripts which can then be run from within `BTB-manager-telegram` by navigating to `🛠 Maintenance` > `🤖 Execute custom script`.

## Setup

To setup your custom scripts, create a file called **`custom_scripts.json`** inside `BTB-manager-telegram`'s **`config`** directory.  
You can use the `custom_scripts_example.json` file as an example for how the file's content should be formatted.

## Adding custom scripts

In the `custom_scripts.json` file the `key` represents the command's name (_what will be shown on the button_), while the `value` represents the command that needs to be executed.

For example if one wants a button called `List files` which executes the `ls -la -R` command, the `custom_scripts.json` file's content should be the following:

```json
{
  "List files": "ls -la -R"
}
```

Multiple scripts can be setup by adding a new line to the json file like so:

```json
{
  "List files": "ls -la -R",
  "List files 2": "ls -la -R"
}
```
