import os, json, logging, tornado.web, twilio.twiml
from sys import argv, exit
from time import sleep

from core.api import MPServerAPI

MINUS_KEY = 1
POUND_KEY = 2
PLUS_KEY = 3
SLASH_KEY = 4

KEY_MAP = {
	'choose_main_menu' : [
		(MINUS_KEY, 'choose_somebody_impressed_you', 'gather'), 
		(POUND_KEY, 'choose_you_are_a_criminal', 'gather'), 
		(PLUS_KEY, 'choose_tattoo_out_of_style', 'gather'), 
		(SLASH_KEY, 'choose_body_image', 'gather')
	],
	'choose_somebody_impressed_you' : [
		(MINUS_KEY, 'choose_in_a_movie', 'gather'),
		(SLASH_KEY, 'choose_at_a_party', 'gather'),
		(POUND_KEY, 'hear_trying_very_hard', 'terminus')
	],
	'choose_you_are_a_criminal' : [
		(POUND_KEY, 'choose_reading', 'gather'),
		(PLUS_KEY, 'choose_exercise', 'reroute', {
			'next_route' : 'choose_main_menu',
			'play_music' : True
		})
	],
	'choose_reading' : [
		(POUND_KEY, 'hear_political_text', 'reroute', {
			'next_route' : 'choose_main_menu',
			'play_music' : True
		}),
		(SLASH_KEY, 'hear_religious_text', 'terminus')
	],
	'choose_tattoo_out_of_style' : [
		(POUND_KEY, 'choose_corset_legs', 'reroute', 'choose_main_menu'),
		(PLUS_KEY, 'hear_mom', 'terminus'),
		(SLASH_KEY, 'hear_tribal_tattoos', 'terminus'),
		(MINUS_KEY, 'choose_so_called_tramp_stamp', 'reroute', {
			'next_route' : 'choose_body_image',
			'play_music' : True
		})
	],
	'choose_body_image' : [
		(POUND_KEY, 'hear_suffer_from_invisibility', 'terminus'),
		(SLASH_KEY, 'hear_specific_body_part', 'terminus'),
		(MINUS_KEY, 'hear_overall_shape', 'reroute', {
			'next_route' : 'choose_main_menu',
			'play_music' : True
		}),
		(PLUS_KEY, 'choose_hair', 'gather')
	],
	'choose_in_a_movie' : [
		(POUND_KEY, 'hear_too_smart', 'terminus'),
		(SLASH_KEY, 'hear_too_beautiful', 'reroute', {
			'next_route' : 'choose_body_image',
			'play_music' : True
		}),
		(PLUS_KEY, 'hear_too_successful', 'terminus')
	],
	'choose_at_a_party' : [
		(MINUS_KEY, 'hear_more_socially_adept', 'terminus'),
		(PLUS_KEY, 'hear_throw_up', 'reroute', {
			'next_route' : 'choose_main_menu',
			'play_music' : True
		}),
		(SLASH_KEY, 'hear_too_successful', 'terminus')
	],
	'choose_empathy_training' : [
		(PLUS_KEY, 'choose_paraphrase', 'gather'),
		(POUND_KEY, 'hear_delay_gratification', 'terminus')
	],
	'choose_paraphrase' : [
		(MINUS_KEY, 'choose_rat_ate_the_malt', 'gather'),
		(SLASH_KEY, 'choose_wrong_paraphrase', 'gather'),
		(PLUS_KEY, 'choose_wrong_paraphrase', 'gather')
	],
	'choose_rat_ate_the_malt' : [
		(PLUS_KEY, 'choose_men_women_nothing', ''),
		(POUND_KEY, 'choose_nothing_nothing_nothing', ''),
		(MINUS_KEY, 'choose_without_man_woman', '')
	],
	'choose_wrong_paraphrase' : [
		(POUND_KEY, 'null_silence', 'reroute', {'next_route' : 'choose_paraphrase'}),
		(MINUS_KEY, 'null_silence', 'terminus')
	],
	'choose_rat_cat_dog' : [],
	'choose_men_women_nothing' : [],
	'choose_nothing_nothing_nothing' : [],
	'choose_without_man_woman' : []
}

class LackOfSelfConfidence(MPServerAPI):
	def __init__(self):
		MPServerAPI.__init__(self)

		self.routes.extend([
			(r'/mapping$', self.TwilioMappingHandler),
			(r'/media/(.*\.wav)', tornado.web.StaticFileHandler, \
				{ 'path' : os.path.join(self.conf['media_dir'], "prompts") })
		])

		self.db.set('default', "choose_main_menu")
		logging.basicConfig(filename=self.conf['d_files']['module']['log'], level=logging.DEBUG)

	class TwilioMappingHandler(tornado.web.RequestHandler):
		def get(self):			
			key = self.get_argument('Digits', None, True)
			session_id = self.get_argument('From', None, True)

			return self.application.on_key_pressed(key, session_id)

	def __twilio_gather(self, extras):
		result = twilio.twiml.Response()

		with result.addGather(numDigits=1, action="/mapping", method="GET") as g:
			g.play(os.path.join("media", "%s.wav" % self.db.get(extras['session_id'])))

		return str(result)

	def __twilio_terminus(self, extras):
		result = twilio.twiml.Response()

		result.addPlay(os.path.join("media", "%s.wav" % self.db.get("current_route")))
		result.addPlay(os.path.join("media", "end_music.wav"))

		return str(self.on_hang_up(result))

	def __twilio_reroute(self, extras):
		result = twilio.twiml.Response()
		
		result.addPlay(os.path.join("media", "%s.wav" % self.db.get("current_route")))

		if 'play_music' in extras.keys() and extras['play_music']:
			result.addPlay(os.path.join("media", "end_music.wav"))
		if 'next_route' in extras.keys():
			self.db.set(extras['session_id'], extras['next_route'])

		return str(result)

	def __route_next(self, prompt_code, extras):
		try:
			route = KEY_MAP[prompt_code]
			if route is None:
				return self.on_hang_up()

			self.db.set(extras['session_id'], prompt_code)
			return getattr(self, "__twilio_%s" % KEY_MAP[prompt_code][2])(extras)
		
		except Exception as e:
			logging.error("could not route next!")
			print e, type(e)

		return self.on_hang_up()

	def on_key_pressed(self, key, session_id):
		# route to next func on stack
		print "OK KEY: %s (type %s)" % (key, type(key))

		try:
			extras = { 'session_id' : session_id }
			
			if len(p) == 4:
				extras.extend(p[3])

			prompt = [p for p in KEY_MAP[self.db.get(extras['session_id'])] if p[0] == key][0]
			return self.__route_next(p[1], extras)
		except Exception as e:
			logging.error("could not grab a prompt code for %s : %d" % \
				(self.db.get(extras['session_id']), key))

			print e, type(e)

		return self.on_hang_up()

	def on_pick_up(self):
		if super(LackOfSelfConfidence, self).on_pick_up()['ok']:
			return self.__route_next('choose_main_menu', {'session_id' : 'default'})

		return self.on_hang_up()

	def on_hang_up(self, response=None):
		super(LackOfSelfConfidence, self).on_hang_up()
		
		if response is None:
			response = twilio.twiml.Response()
			response.addPlay(os.path.join("media", "default_goodbye_response.wav"))
		
		response.addHangup()
		return str(response)

if __name__ == "__main__":
	res = False
	losc = LackOfSelfConfidence()

	if argv[1] in ['--stop', '--restart']:
		res = losc.stop()
		sleep(5)

	if argv[1] in ['--start', '--restart']:
		res = losc.start()

	exit(0 if res else -1)