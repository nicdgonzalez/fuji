import clap

parser = clap.Parser(
    "A command-line tool for managing Minecraft servers.",
    epilog="Thank you for using Fuji!",
)

extensions = [
    ".fuji",
]

for ext in extensions:
    parser.add_extension(ext, package="fuji.ext")
