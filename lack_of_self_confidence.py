import os, json, logging, twilio.twiml
from sys import argv, exit
from time import sleep
from tornado.web import RequestHandler

from core.api import MPServerAPI
from core.vars import DEFAULT_TELEPHONE_GPIO, UNPLAYABLE_FILES

MINUS_KEY = 2
POUND_KEY = 13
PLUS_KEY = 3
SLASH_KEY = 4

PROMPTS = {
	'choose_main_menu' : "choose_main_menu.wav"
}

KEY_MAP = {
	'choose_main_menu' : [MINUS_KEY, POUND_KEY, PLUS_KEY, SLASH_KEY]
}

class LackOfSelfConfidence(MPServerAPI):
	def __init__(self):
		MPServerAPI.__init__(self)

		self.gpio_mappings = DEFAULT_TELEPHONE_GPIO
		self.routes.append((r'/mapping$', self.TwilioMappingHandler))

		logging.basicConfig(filename=self.conf['d_files']['module']['log'], level=logging.DEBUG)

	class TwilioMappingHandler(RequestHandler):
		def get(self):
			logging.debug("here is a mapping from twilio")
			key = self.request.body['Digits']
			
			return self.on_key_pressed(key)

	def hear_hold_music(self):
		return False

	def choose_main_menu(self):
		result = twilio.twiml.Response()
		with result.gather(numDigits=1, action="/mapping", method="GET") as g:
			g.play(PROMPTS['choose_main_menu'])

		return str(result)

	def on_pick_up(self):
		if super(LackOfSelfConfidence, self).on_pick_up()['ok']:
			return self.choose_main_menu()

		return None

	def on_hang_up(self):
		super(LackOfSelfConfidence, self).on_hang_up()
		return None

	def on_key_pressed(self, key):
		# route to next func on stack

		return None

if __name__ == "__main__":
	res = False
	losc = LackOfSelfConfidence()

	if argv[1] in ['--stop', '--restart']:
		res = losc.stop()
		sleep(5)

	if argv[1] in ['--start', '--restart']:
		res = losc.start()

	exit(0 if res else -1)