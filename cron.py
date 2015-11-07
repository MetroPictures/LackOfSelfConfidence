from sys import exit
from lack_of_self_confidence import LackOfSelfConfidence

if __name__ == "__main__":
	losc = LackOfSelfConfidence()
	exit(0 if losc.daily_reset() else -1)