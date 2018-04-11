# Autoflash

This is an easy flashing program for Althea routers and is a work in progress. Use as your own risk at this stage.

	 Usage:
	   autoflash flash [--device=<id>] [--loop] [--tmpdir=<dir>] [-v] [--vv]
	   autoflash list-devices [-v] [--vv]
	   autoflash download --device=<id> [--tmpdir=<dir>] [-v] [--vv]

	Options:
	  --device=<id>          Device id to flash [default: None]
	  --loop                 Repeat the flash on a loop to flash many identical devices
	  --tmpdir=<dir>         Filepath for the storage of Althea firmware files 	[default: Current Directory]
	  -v                     Application level debugging
	  -vv                    Library level debugging

