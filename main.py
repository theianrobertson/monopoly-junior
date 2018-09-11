from collections import Counter
from itertools import cycle
import logging
import sys
from dataclasses import dataclass
import random

import yaml

LOG = logging.getLogger(__name__)

DIE_OPTIONS = [1, 2, 'chance', 4, 5, 6]
STARTING_MONEY = {2: 18, 3: 14, 4: 14}
STARTING_PRESENTS = 8
GO_SALARY = 2

with open('squares.yaml') as file_open:
    SQUARES = yaml.load(file_open)
    SQUARES = [{'index': i, **sq} for i, sq in enumerate(SQUARES)]
with open('chance-cards.yaml') as file_open:
    CHANCE_CARDS = yaml.load(file_open)

def die_roll():
    return random.choice(DIE_OPTIONS)

def shuffle_chance_cards():
    chance_cards = CHANCE_CARDS
    random.shuffle(chance_cards)
    return chance_cards

@dataclass
class Player:
    name: str
    money: int
    squares_owned: set
    current_square: int = 0
    presents: int = STARTING_PRESENTS
    in_jail: bool = False
    has_get_out_of_jail_card: bool = False

    def add_money(self, amount):
        if amount <= 0:
            LOG.debug('Subtracting {} from player {}'.format(-amount, self.name))
        else:
            LOG.debug('Adding {} to player {}'.format(amount, self.name))
        self.money += amount
        if self.money <= 0:
            LOG.debug("Player {} is bankrupt!".format(self.name))
            raise ValueError("Player {} is bankrupt!".format(self.name))

    def buy_square(self, square, cost):
        """Buy a square by deducting the cost, adding the name to the set of squares owned, and
        removing a present."""
        LOG.debug('Player {} is buying {} for ${}'.format(self.name, square, cost))
        self.add_money(-cost)
        self.squares_owned.add(square)
        self.presents -= 1

    @property
    def total_money(self):
        return self.money + len(self.squares_owned)

    def leave_jail(self):
        if self.in_jail:
            LOG.debug('Player {} leaving jail'.format(self.name))
            if self.has_get_out_of_jail_card:
                LOG.debug('Using get out of jail card')
                self.has_get_out_of_jail_card = False
                self.in_jail = False
            else:
                self.add_money(-1)
                self.in_jail = False


class Game:
    def __init__(self, players):
        self.players = players
        self.party_box_balance = 0
        self.chance_cards = shuffle_chance_cards()

    @property
    def owned_squares(self):
        """All of the squares that are owned"""
        return set().union(*[player.squares_owned for player in self.players])

    def draw_chance_card(self):
        chance_card = self.chance_cards.pop(0)
        self.chance_cards.append(chance_card)
        return chance_card

    def who_owns(self, square):
        return [player for player in self.players if square in player.squares_owned][0]

    def move_die_number(self, player, die_number):
        """Move the die number"""
        player.leave_jail()
        new_square_index = player.current_square + die_number
        if new_square_index >= 24:
            #Add salary for passing go
            player.add_money(GO_SALARY)
        new_square = SQUARES[new_square_index % 24]
        LOG.debug('Player {} moving to square {}'.format(player.name, new_square['square']))
        player.current_square = new_square_index % 24

        if new_square['square'] in set(['Go', 'Free Parking', 'Jail']).union(player.squares_owned):
            pass
        elif new_square['square'] == 'Go to Jail':
            player.in_jail = True
            player.current_square = [sq['index'] for sq in SQUARES if sq['square'] == 'Jail'][0]
        elif new_square['square'] == 'Chance':
            self.chance(player)
        elif new_square['square'] == 'Party Box':
            player.add_money(self.party_box_balance)
            self.party_box_balance = 0

        #Now it should be a party square that's not owned or owned by someone else.
        elif new_square['square'] not in self.owned_squares:
            player.buy_square(new_square['square'], new_square['cost'])
        else:
            to_pay = self.who_owns(new_square['square'])
            player.add_money(-new_square['cost'])
            to_pay.add_money(new_square['cost'])

    def chance(self, player):
        """Do a chance card action.  Note, the "go to and get" action will choose the first square
        on the board both to buy when there are two available, and to pay."""
        chance_card = self.draw_chance_card()
        LOG.debug('Player {} drew chance type {}'.format(player.name, chance_card['type']))
        if chance_card['type'] == 'goto-and-get':
            colour_squares = [sq for sq in SQUARES if sq.get('colour') == chance_card['colour']]
            self_owned = [sq for sq in colour_squares if sq['square'] in player.squares_owned]
            unowned = [sq for sq in colour_squares if sq['square'] not in self.owned_squares]
            LOG.debug('Moving to one of {}: player owns {}, {} are unowned'.format(
                colour_squares, self_owned, unowned))
            if unowned:
                #Just buy the first one
                player.buy_square(unowned[0]['square'], cost=0)
            else:
                if self_owned:
                    #Just go to your first one
                    player.current_square = self_owned[0]['index']
                else:
                    #Just go to the first one
                    new_square = colour_squares[0]
                    player.current_square = new_square['index']
                    to_pay = self.who_owns(new_square['square'])
                    player.add_money(-new_square['cost'])
                    to_pay.add_money(new_square['cost'])

        elif chance_card['type'] == 'goto':
            player.current_square = 0
            player.add_money(GO_SALARY)
        elif chance_card['type'] == 'pay-into-party-box':
            player.add_money(-chance_card['amount'])
        elif chance_card['type'] == 'get-out-of-jail-free':
            player.has_get_out_of_jail_card = True
        else:
            raise ValueError('Unexpected chance card type: {}'.format(chance_card['type']))

    def take_turn(self, player):
        """Roll the die and take the turn"""
        roll = die_roll()
        LOG.debug('Player {} rolled a {}'.format(player.name, roll))
        if roll == 'chance':
            self.chance(player)
        else:
            self.move_die_number(player, roll)

    def play(self):
        for turn_count, player in enumerate(cycle(self.players)):
            try:
                self.take_turn(player)
            except ValueError:
                LOG.debug("Player {} is bankrupt!".format(player.name))
                return self.get_winners(), turn_count + 1

    def get_winners(self):
        top_score = max([player.total_money for player in self.players])
        top_scorers = [player.name for player in self.players if player.total_money == top_score]
        LOG.info("Player(s) {} won the game with {} dollars!".format(
            ', '.join(top_scorers), top_score))
        return top_scorers

if __name__ == '__main__':
    if len(sys.argv) > 1:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        number_of_iterations = int(sys.argv[1])
    else:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        number_of_iterations = 1

    winners = Counter()
    game_lengths = Counter()
    for i in range(number_of_iterations):
        LOG.info('Playing game {} of {}'.format(i + 1, number_of_iterations))
        player_1 = Player('Son', STARTING_MONEY[2], set())
        player_2 = Player('Dad', STARTING_MONEY[2], set())
        game = Game([player_1, player_2])
        winner, game_length = game.play()
        winners[winner[0]] += 1
        game_lengths[game_length] += 1
    LOG.info('Total wins: {}'.format(winners))
    LOG.info('Game length distribution: {}'.format(game_lengths))
