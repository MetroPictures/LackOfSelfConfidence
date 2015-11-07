import os, json, logging, tornado.web, twilio.twiml, redis
from sys import argv, exit
from time import sleep

from core.api import MPServerAPI
from core.utils import get_config, num_to_hash

BASE_URL, NUM_SALT, MAX_DAILY_CALLS = get_config(['base_url', 'our_salt', 'max_daily_calls'])
DAILY_CALLS = 1
GLOBAL_BLACKLIST = 2

ONE = 1
TWO = 2
THREE = 3
FOUR = 4

KEY_MAP = {
	'1_LackofSelfConfidenceMenu':[
		'2_SomebodyImpressedYouMenu',
		'10_YouAreACriminalMenu',
		'23_TattooOutofStyleMenu',
		'28_BodyImageMenu'
	],
	'2_SomebodyImpressedYouMenu':[
		'3_InAMovieMenu',
		'9_ButTryingVeryHardEnd',
		'2_SomebodyImpressedYouMenu',
		'6_AtAPartyMenu',
	],
	'3_InAMovieMenu':[
		'3_InAMovieMenu',
		'4_TooSmartEnd',
		'5_TooSuccessfulEnd',
		'3_InAMovieMenu'	#too beautiful missing?
	],
	'4_TooSmartEnd':None,
	'5_TooSuccessfulEnd':None,
	'6_AtAPartyMenu':[
		'7_MoreSociallyAdeptEnd',
		'6_AtAPartyMenu',
		'8_NotThrowUpEnd',
		'7_MoreSociallyAdeptEnd'
	],
	'7_MoreSociallyAdeptEnd':None,
	'8_NotThrowUpEnd':'1_LackofSelfConfidenceMenu',
	'9_ButTryingVeryHardEnd':None,
	'10_YouAreACriminalMenu':[
		'10_YouAreACriminalMenu',
		'11_ReadingMenu',
		'15_EmpathyTrainingMenu',
		'14_ExerciseEnd'
	],
	'11_ReadingMenu':[
		'11_ReadingMenu',
		'12_PoliticsReadingEnd',
		'11_ReadingMenu',
		'13_ReligiousReadingEnd'
	],
	'12_PoliticsReadingEnd':'1_LackofSelfConfidenceMenu',
	'13_ReligiousReadingEnd':None,
	'14_ExerciseEnd':'1_LackofSelfConfidenceMenu',
	'15_EmpathyTrainingMenu':[
		'15_EmpathyTrainingMenu',
		'22_DelayGratificationEnd',
		'16_ParaphraseMenu'
	],
	'16_ParaphraseMenu':[
		'17_TheRatAteTheMaltMenu',
		'16_ParaphraseMenu',
		'20_TheRatChasedTheCatMenu',
		'20_TheRatChasedTheCatMenu'
	],
	'17_TheRatAteTheMaltMenu':[
		'18_BuffaloMenu',
		'18_BuffaloMenu',
		'18_BuffaloMenu',
		'18_BuffaloMenu'
	],
	'18_BuffaloMenu':[
		'19_BuffaloEnd',
		'18_BuffaloMenu',
		'19_BuffaloEnd',
		'19_BuffaloEnd'
	],
	'19_BuffaloEnd':None,
	'20_TheRatChasedTheCatMenu':[
		'21_TryAgainNoEnd',
		'16_ParaphraseMenu'
	],
	'21_TryAgainNoEnd':None,
	'22_DelayGratificationEnd':None,
	'23_TattooOutofStyleMenu':[
		'27_TrampStampEnd',
		'24_CorsetLegsEnd',
		'25_MomEnd',
		'26_TribalTattooEnd'
	],
	'24_CorsetLegsEnd':'1_LackofSelfConfidenceMenu',
	'25_MomEnd':None,
	'26_TribalTattooEnd':None,
	'27_TrampStampEnd':'28_BodyImageMenu',
	'28_BodyImageMenu':[
		'31_OverallShapeEnd',
		'29_InvisibilityEnd',
		'32_HairMenu',
		'30_SpecificBodyPartEnd'
	],
	'29_InvisibilityEnd':'1_LackofSelfConfidenceMenu',
	'30_SpecificBodyPartEnd':None,
	'31_OverallShapeEnd':'1_LackofSelfConfidenceMenu',
	'32_HairMenu':[
		'36_TooDryEnd',
		'35_TooStraightEnd',
		'33_TooTanglyEnd',
		'34_TooCurlyEnd'
	],
	'33_TooTanglyEnd':'1_LackofSelfConfidenceMenu',
	'34_TooCurlyEnd':'1_LackofSelfConfidenceMenu',
	'35_TooStraightEnd':'1_LackofSelfConfidenceMenu',
	'36_TooDryEnd':'1_LackofSelfConfidenceMenu',
}

class LackOfSelfConfidence(MPServerAPI):
	def __init__(self):
		MPServerAPI.__init__(self)

		self.routes.extend([
			(r'/mapping$', self.TwilioMappingHandler),
			(r'/media/(.*\.mp3)', tornado.web.StaticFileHandler, \
				{ 'path' : os.path.join(self.conf['media_dir'], "prompts") })
		])

		self.db.set('default', "choose_main_menu")
		
		self.daily_calls = redis.StrictRedis(host='localhost', port=self.conf['redis_port'], db=DAILY_CALLS)
		self.global_blacklist = redis.StrictRedis(host='localhost', port=self.conf['redis_port'], db=GLOBAL_BLACKLIST)

		logging.basicConfig(filename=self.conf['d_files']['module']['log'], level=logging.DEBUG)

	class TwilioMappingHandler(tornado.web.RequestHandler):
		def get(self):			
			key = self.get_argument('Digits', None, True)
			phone_number = self.get_argument('From', None, True)

			response = self.application.on_key_pressed(key, num_to_hash(phone_number, NUM_SALT))
			logging.debug(str(response))

			self.finish(str(response))

	def __twilio_prompt(self, prompt):
		result = twilio.twiml.Response()

		with result.addGather(numDigits=1, action="/mapping", method="GET") as g:
			g.play(os.path.join("media", "%s.mp3" % prompt))

		return result

	def __twilio_say(self, prompt):
		result = twilio.twiml.Response()
		result.play(os.path.join("media", "%s.mp3" % prompt))

		return result

	def __twilio_redirect(self, prompt):
		result = twilio.twiml.Response()
		result.addPlay(os.path.join("media", "%s.mp3" % prompt))
		result.addRedirect("%s:%d/mapping" % (BASE_URL, self.conf['api_port']), method="GET")

		return result

	def __twilio_hangup(self, prompt):
		result = twilio.twiml.Response()

		if prompt is not None:
			result.addPlay(os.path.join("media", "%s.mp3" % prompt))
		
		result.addHangup()

		super(LackOfSelfConfidence, self).on_hang_up()
		return result

	def __twilio_reject(self):
		result = twilio.twiml.Response()
		result.addReject()

		return result

	def daily_reset(self):
		self.daily_calls.flushdb()
		return True

	def report_abusive_number(self, dipshit):
		try:
			global_blacklist = json.loads(self.global_blacklist.get("global_blacklist"))
		except Exception as e:
			print "No global blacklist yet, though..."
			global_blacklist = []

		global_blacklist.append(dipshit)
		self.global_blacklist.set("global_blacklist", json.dumps(global_blacklist))

		return True

	def route_next(self, session_id, init=False):
		if init:
			prompt = '1_LackofSelfConfidenceMenu'
		else:
			prompt = self.db.get(session_id)

		if KEY_MAP[prompt] is None:
			return self.__twilio_hangup(prompt)

		if type(KEY_MAP[prompt]) in [str, unicode]:
			self.db.set(session_id, KEY_MAP[prompt])
			return self.__twilio_redirect(prompt)

		return self.__twilio_prompt(prompt)

	def on_key_pressed(self, key, session_id):
		# route to next func on stack
		#print "OK KEY: %s (type %s)" % (key, type(key))
		#print "FROM SESSION ID %s" % session_id			

		try:
			last_prompt = self.db.get(session_id)
		except Exception as e:
			logging.debug("could not get any info for this session id %s. probably does not exist." % session_id)
			print e, type(e)
		
		if not last_prompt:
			last_prompt = '1_LackofSelfConfidenceMenu'

		#print "LAST PROMPT: %s" % last_prompt
		#print "ITS KEYS: %s" % KEY_MAP[last_prompt]

		if KEY_MAP[last_prompt] is None:
			return self.__twilio_hangup(last_prompt)

		next_prompt = None

		if key is not None:
			key = (int(key) - 1)
			if key not in range(len(KEY_MAP[last_prompt])):
				next_prompt = last_prompt
			else:
				next_prompt = KEY_MAP[last_prompt][key]

		if next_prompt is None:
			next_prompt = last_prompt

		try:
			self.db.set(session_id, next_prompt)
			return self.route_next(session_id)
		except Exception as e:
			logging.error("could not grab a prompt code for %s : %d" % \
				(self.db.get('session_id'), key))

			print e, type(e)

		return self.__twilio_hangup(None)

	def in_master_blacklist(self, phone_number):
		print "is %s in master blacklist?" % phone_number

		try:
			global_blacklist = json.loads(self.global_blacklist.get("global_blacklist"))
		except Exception as e:
			print "No global blacklist yet, hooray!"
			return False

		if phone_number not in global_blacklist:
			return False

		return True

	def daily_calls_exceeded(self, session_id):
		print "has %s used up all its calls today?" % session_id

		try:
			daily_calls = int(self.daily_calls.get(session_id))
			print "caller %s has used up %d calls today." % (session_id, daily_calls)
		except Exception as e:
			print "Daily calls not initialized yet!"
			daily_calls = 0

		if daily_calls >= MAX_DAILY_CALLS:
			return True

		self.daily_calls.set(session_id, (daily_calls + 1))
		return False

	def on_pick_up(self, phone_number):
		if self.in_master_blacklist(phone_number):
			return str(self.__twilio_reject())

		# number masking begins once we verify caller is not an abuser.
		session_id = num_to_hash(phone_number, NUM_SALT)

		if self.daily_calls_exceeded(session_id):
			return str(self.__twilio_reject())

		self.db.delete(session_id)
		return str(self.route_next(session_id, init=True))

	def start(self):
		if not super(LackOfSelfConfidence, self).start():
			return False

		from crontab import CronTab
		from core.vars import BASE_DIR

		cron = CronTab(user=True)
		
		job = cron.new(command="python %s" % os.path.join(BASE_DIR, "cron.py"))
		job.day.every(1)
		job.enable()

		return job.is_enabled()

	def stop(self):
		from crontab import CronTab
		from core.vars import BASE_DIR

		cron = CronTab(user=True)
		
		for job in cron:
			job.enable(False)

		cron.remove_all()

		return super(LackOfSelfConfidence, self).stop()

if __name__ == "__main__":
	res = False
	losc = LackOfSelfConfidence()

	if argv[1] in ['--stop', '--restart']:
		res = losc.stop()
		sleep(5)

	if argv[1] in ['--start', '--restart']:
		res = losc.start()

	exit(0 if res else -1)