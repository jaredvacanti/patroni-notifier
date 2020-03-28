import yaml
from patroni_notifier import click


def update_context_with_config_file(ctx, file_name):
    config_file = ctx.params[file_name]
    if config_file is not None:
        with open(config_file) as f:
            config_data = yaml.safe_load(f)
            for param, value in ctx.params.items():
                if param in config_data:
                    ctx.params[param] = config_data[param]
            # for param in ctx.command.params:
            #     if param.name in config_data:
            #         if param.default != config_data[param.name]:
            #             param.default = config_data[param.name]

    return ctx


def CommandWithConfigFileHelper(config_file_param_name):
    class CommandWithConfigFile(click.Command):

        def invoke(self, ctx):
            ctx = update_context_with_config_file(ctx, config_file_param_name)
            return super(CommandWithConfigFile, self).invoke(ctx)

        def get_help(self, ctx):
            """Formats the help into a string and returns it.
            Calls :meth:`format_help` internally.
            """
            # ctx = update_context_with_config_file(ctx, config_file_param_name)
            print("get help")
            formatter = ctx.make_formatter()
            self.format_help(ctx, formatter)
            return formatter.getvalue().rstrip("\n")

    return CommandWithConfigFile
