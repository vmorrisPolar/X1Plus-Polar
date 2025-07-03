"""
Module to allow printing using Polar Cloud service.

[X1PLUS_MODULE_INFO]
module:
  name: polar_cloud
[END_X1PLUS_MODULE_INFO]
"""

import asyncio
import logging
import os
import socketio
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from base64 import b64encode

import x1plus
from x1plus.utils import get_MAC, serial_number, is_emulating

logger = logging.getLogger(__name__)


class PolarPrintService:
    def __init__(self, daemon):
        self.daemon = daemon
        self.polar_sn = self.daemon.settings.get("polar.serial_number", "")
        # Todo: VERY IMPORTANT!! The public and private keys MUST be moved to
        # non-volatile memory before release.
        self.public_key = self.daemon.settings.get("polar.public_key", "")
        self.private_key = self.daemon.settings.get("polar.private_key", "")
        self.connected = False
        self.connection_status = "Not connected"
        self.mac = ""
        self.pin = ""
        self.username = ""
        self.server_url = "https://printer2.polar3d.com"
        self.socket = None
        # self.ip = ""
        # Watch for settings changes
        self.daemon.settings.on("polar.enabled", self._on_enabled_changed)
        self.daemon.settings.on("polar.username", self._on_creds_changed)
        self.daemon.settings.on("polar.pin", self._on_creds_changed)


    async def begin(self):
        """Create Socket.IO client and connect to server."""
        try: 
            self.socket = socketio.AsyncClient()
            self.set_interface()
            await self.get_creds()
            await self.socket.connect(self.server_url, transports=["websocket"])
            # Assign socket callbacks.
            self.socket.on("registerResponse", self._on_register_response)
            self.socket.on("keyPair", self._on_keypair_response)
            self.socket.on("helloResponse", self._on_hello_response)
            self.socket.on("welcome", self._on_welcome)
            self.socket.on("delete", self._on_delete)
        except Exception as e:
            logger.error(f"Failed to start polar_cloud: {e.__class__.__name__}: {e}")
            if self.socket:
                self.socket.disconnect()


    async def _on_welcome(self, response, *args, **kwargs):
        """
        Check to see if printer has already been registered. If it has, we can
        ignore this. Otherwise, must get a key pair, then call register.
        """
        logger.info("_on_welcome.")
        logger.debug(f"challenge: {response['challenge']}")
        logger.debug(
            f"Polar SN: {self.polar_sn}, Public key exists: {bool(self.public_key)}"
        )
        # Two possibilities here. If it's already registered there should be a
        # Polar Cloud serial number and a set of RSA keys. If not, then must
        # request keys first.
        if self.polar_sn and self.public_key:
            # The printer has been registered. Note that
            # we're now using the serial number assigned by the server.
            # First, encode challenge string with the private key.
            logger.debug(f"challenge: {response['challenge']}")
            # The printer has been registered.
            # First, encode challenge string with the private key.
            private_key = self.private_key.encode("utf-8")
            rsa_key = RSA.import_key(private_key)
            hashed_challenge = SHA256.new(response["challenge"].encode("utf-8"))
            key = pkcs1_15.new(rsa_key)
            data = {
                "serialNumber": self.polar_sn,
                "signature": b64encode(key.sign(hashed_challenge)).decode("utf-8"),
                "MAC": self.mac,
                "protocol": "2.0",
                "mfgSn": self.serial_number(),
            }
            """
            Note that the following optional fields might be used in future.
            "printerMake": "printer make",                     // string, optional
            "version": "currently installed software version", // string, optional
            "localIP": "printer's local IP address",           // string, optional
            "rotateImg": 0 | 1,                                // integer, optional
            "transformImg": 0 - 7,                             // integer, optional
            "camOff": 0 | 1,                                   // integer, optional
            "camUrl": "URL for printer's live camera feed"     // string, optional
            """
            await self.socket.emit("hello", data)
        elif not self.polar_sn and not self.public_key:
            # We need to get an RSA key pair before we can go further.
            # Todo: This needs to be moved locally rather than being remote, so
            # private key isn't transmitted.
            await self.socket.emit("makeKeyPair", {"type": "RSA", "bits": 2048})
        elif not self.polar_sn:
            # We already have a key: just register.
            logger.info(f"_on_welcome Registering.")
            await self._register()
        else:
            # It's not possible to have a serial number and no key, so this
            # would be a real problem.
            logger.error("Somehow have an SN and no key.")
            exit()

    def _on_hello_response(self, response, *args, **kwargs):
        if response["status"] == "SUCCESS":
            logger.info("_on_hello_response success")
        else:
            logger.error(f"_on_hello_response failure: {response['message']}")
            # Deal with error here.

    async def _on_keypair_response(self, response, *args, **kwargs):
        """
        Request a keypair from the server. On success register. On failure kick
        out to interface for new email or pin.
        """
        if response["status"] == "SUCCESS":
            self.public_key = response["public"]
            self.private_key = response["private"]
            # Save keys to settings
            self.daemon.settings.put("polar.public_key", self.public_key)
            self.daemon.settings.put("polar.private_key", self.private_key)
            # We have keys, but still need to register. First disconnect.
            logger.info("_on_keypair_response success. Disconnecting.")
            # Todo: I'm not creating a race condition with the next three fn calls, am I?
            await self.socket.disconnect()
            # After the next line it will send a `welcome`.
            logger.info("Reconnecting.")
            await self.socket.connect(self.server_url, transports=["websocket"])
        else:
            # We have an error.
            error_msg = response.get('message', 'Key pair request failed')
            logger.error(f"_on_keypair_response failure: {error_msg}")
            self.connection_status = f"Key Error: {error_msg}"
            self.daemon.settings.put("polar.last_error", error_msg)
            self._update_status()

    async def _on_register_response(self, response, *args, **kwargs):
        """Get register response from status server and save serial number."""
        if response["status"] == "SUCCESS":
            logger.info("_on_register_response success.")
            logger.debug(f"Serial number: {response['serialNumber']}")
            self.polar_sn = response["serialNumber"]
            self.daemon.settings.put("polar.serial_number", self.polar_sn)
            self.connection_status = "Connected"
            self.connected = True
            # Clear any previous errors
            self.daemon.settings.put("polar.last_error", "")
            self._update_status()
            logger.info(f"Successfully registered with Polar Cloud. Serial: {self.polar_sn}")

        else:
            # We have an error.
            error_msg = response.get('reason', 'Registration failed')
            logger.error(f"_on_register_response failure: {error_msg}")
            self.connection_status = f"Registration Error: {error_msg}"
            self.daemon.settings.put("polar.last_error", error_msg)
            self._update_status()
            # Todo: deal with various failure modes here. Most can be dealt
            # with in interface. First three report as server erros? Modes are
            # "SERVER_ERROR": Report this?
            # "MFG_UNKNOWN": Again, should be impossible.
            # "INVALID_KEY": Ask for new key. Maybe have a counter and fail after two?
            # "MFG_MISSING": This should be impossible.
            # "EMAIL_PIN_ERROR": Send it to the interface.
            # "FORBIDDEN": There's an issue with the MAC address.
            if response["reason"].lower() == "forbidden":
                # Todo: Must communicate with dbus to debug this!
                logger.error(
                    f"Forbidden. Duplicate MAC problem!\nTerminating MAC: "
                    f"{self.mac}\n\n"
                )
                exit()

    async def _register(self):
        """
        Send register request. Note this can only be called after a keypair
        has been received and stored.
        """
        if is_emulating:
            sn = "123456789"
        else:
            sn = serial_number()
        logger.info("_register.")
        data = {
            "mfg": "bambu",
            "email": self.username,
            "pin": self.pin,
            "publicKey": self.public_key,
            "mfgSn": sn,
            "myInfo": {"MAC": self.mac},
        }
        await self.socket.emit("register", data)

    async def _status(self) -> None:
        """
        Should send several times a minute (3? 4?). All fields but serialNumber
        and status are optional.
        {
            "serialNumber": "string",
            "status": integer,
            "progress": "string",
            "progressDetail": "string",
            "estimatedTime": integer,
            "filamentUsed": integer,
            "startTime": "string",
            "printSeconds": integer,
            "bytesRead": integer,
            "fileSize": integer,
            "tool0": floating-point,
            "tool1": floating-point,
            "bed": floating-point,
            "chamber": floating-point,
            "targetTool0": floating-point,
            "targetTool1": floating-point,
            "targetBed": floating-point,
            "targetChamber": floating-point,
            "door": integer,
            "jobId": "string",
            "file": "string",
            "config": "string"
        }
        Possible status codes are:
        0     Ready; printer is idle and ready to print
        1     Serial; printer is printing a local print over its serial connection
        2     Preparing; printer is preparing a cloud print (e.g., slicing)
        3     Printing; printer is printing a cloud print
        4     Paused; printer has paused a print
        5     Postprocessing; printer is performing post-printing operations
        6     Canceling; printer is canceling a print from the cloud
        7     Complete; printer has completed a print job from the cloud
        8     Updating; printer is updating its software
        9     Cold pause; printer is in a "cold pause" state
        10     Changing filament; printer is in a "change filament" state
        11     TCP/IP; printer is printing a local print over a TCP/IP connection
        12     Error; printer is in an error state
        13     Disconnected; controller's USB is disconnected from the printer
        14     Door open; unable to start or resume a print
        15     Clear build plate; unable to start a new print
        """
        pass

    def _on_hello_response(self, response, *args, **kwargs):
        if response["status"] == "SUCCESS":
            logger.info("_on_hello_response success")
        else:
            logger.error(f"_on_hello_response failure: {response['message']}")
            # Deal with error here.

    async def _on_delete(self, response, *args, **kwargs) -> None:
        """
        Printer has been deleted from Polar Cloud. Remove all identifying information
        from card. The current print should finish. Disconnect socket so that
        username and PIN don't keep being requested and printer doesn't reregister.
        """
        if response["serialNumber"] == self.daemon.settings.get("polar.sn"):
            self.sn = ""
            self.username = ""
            self.public_key = ""
            self.private_key = ""
            self.pin = ""
            self.mac = ""
            self.username = ""
            # Todo: stop status() here?
            self.socket.disconnect()

    async def get_creds(self) -> None:
        """
        Get credentials from settings or from env file.
        Priority:
        1. X1Plus settings (from UI)
        2. /mnt/sdcard/x1plus/env file
        """
        # First try to get from settings
        self.username = self.daemon.settings.get("polar.username", "")
        self.pin = self.daemon.settings.get("polar.pin", "")
        
        # If not in settings, try env file
        if not self.username or not self.pin:
            try:
                env_path = "/mnt/sdcard/x1plus/env"
                if os.path.exists(env_path):
                    with open(env_path) as env:
                        for line in env:
                            if '=' in line:
                                k, v = line.strip().split('=', 1)
                                if k == 'username' and not self.username:
                                    self.username = v
                                    self.daemon.settings.put("polar.username", v)
                                elif k == 'pin' and not self.pin:
                                    self.pin = v
                                    self.daemon.settings.put("polar.pin", v)
                    logger.info(f"Loaded credentials from {env_path}")
            except Exception as e:
                logger.error(f"Failed to read env file: {e}")
        
        if is_emulating():
            # For emulation, also check local .env file
            try:
                from pathlib import Path
                env_dir = Path(__file__).resolve()
                with open(env_dir.parents[0] / ".env") as env:
                    for line in env:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            setattr(self, k, v)
            except:
                pass

    def set_interface(self):
        """Get IP and MAC addresses and store them in self.settings."""
        self.mac = get_MAC()
        # self.ip = get_IP()
    
    def _update_status(self):
        """Update settings with current connection status."""
        self.daemon.settings.put("polar.connection_status", self.connection_status)
        self.daemon.settings.put("polar.connected", self.connected)
    
    def _on_enabled_changed(self, enabled):
        """Handle when polar.enabled setting changes."""
        if enabled and not self.connected:
            asyncio.create_task(self.begin())
        elif not enabled and self.connected:
            if self.socket:
                asyncio.create_task(self.socket.disconnect())
    
    def _on_creds_changed(self, value):
        """Handle when credentials change."""
        # If we're connected, restart with new creds
        if self.connected:
            asyncio.create_task(self.socket.disconnect())
            asyncio.create_task(self.begin())

_daemon = None
def load(daemon):
    _daemon = daemon
    setattr(daemon, "polar_cloud", PolarPrintService(daemon=daemon))

def start(daemon):
    asyncio.create_task(daemon.polar_cloud.begin())
