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

Multiple scripts can be setup by adding a new line to the json file like so (note the `,` when adding a new line):

```json
{
  "List files": "ls -la -R",
  "List files 2": "ls -la -R"
}
```

## Further information

By default, all scripts are executed from within `BTB-manager-telegram`'s directory.

It is recommended to use the `custom_scripts` directory in order to avoid confusion:

```bash
cd /path/to/the/BTB-manager-telegram/custom_scripts
```

## Example custom script installation

Create a script in a file called `custom_progress.sh` inside the `custom_scripts` directory, you can use this [example script](https://discord.com/channels/811277527997087745/818862057704390700/851190591454314539) from our Discord server.

Make the script executable by giving execute permissions:

```bash
chmod +x custom_progress.sh
```

In our example, the script uses `sqlite3`, so it is necessary to install it via system package manager:

```bash
sudo apt install sqlite3
```

Now we need to modify `custom_scripts.json` (it is located at `~/BTB-manager-telegram/config/custom_scripts.json`):

```json
{
  "Custom Progress": "custom_scripts/custom_progress.sh"
}
```

Do not forget to restart `BTB-manager-telegram` bot so the changes will be applied.
