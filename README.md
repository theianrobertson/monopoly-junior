# Losing at Monopoly Junior

![Monopoly Board](/box.jpg)

Simulating Monopoly Junior to find out why I keep losing

## Background

My son (four) got this board game for a present, and sometimes we play.  Being that he's four, the
game can take a decent amount of time to finish.  For some strange reason he also always seems to
beat me, which leads me to not have nearly as much fun playing the game as I could.

So I figured I'd borrow a page from Jake VanderPlas' [excellent blog
post](http://jakevdp.github.io/blog/2017/12/18/simulating-chutes-and-ladders/) simulating snakes &
ladders, and figure out if my son actually has a legitimate unfair advantage.

## Code

Note, this code is pretty sloppy.  Run `python main.py`, with an optional number of iterations to run
simulations.  I use pyyaml just to load the yaml files (probably not really necessary).

More to come - will write up findings as I iron out a last couple of kinks in the code.
