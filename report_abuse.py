from sys import exit, argv
from lack_of_self_confidence import LackOfSelfConfidence

if __name__ == "__main__":
	if len(argv) != 2:
		print "please submit a number to report!"
		exit(-1)

	losc = LackOfSelfConfidence()
	exit(0 if losc.report_abusive_number(argv[1]) else -1)