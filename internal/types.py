import re
import sys
import networkx as nx
from copy import deepcopy
from random import shuffle
from collections import deque
from matplotlib import pyplot

# ENDED: Numpy arrays giving a headache in logits conversion
# TODO: draw() player routes with separate colors
# TODO: any empty variables in the game object must be set to none when not in use.
# TODO: always update the current player object!!
# TODO: verify that game translation to network input is valid
# TODO: test network output to logit conversion!

"""
CLASSES
--------------------------------------------
"""

class Deck:
    """
    The object to represent a deck of cards in Ticket to Ride
    """
    def __init__(self, items: list) -> None:
        """
        Create a new, shuffled deck of cards from a list of items (no typecast for items within)
        """
        shuffle(items)
        self.cards = deque(items)

    def __str__(self) -> str:
        strings: list[str] = []
        for card in self.cards:
            strings.append(str(card))
        return '\n'.join(strings)
    
    def count(self) -> int:
        """
        The number of cards in this deck
        """
        return len(self.cards)
    
    def shuffle(self) -> None:
        """
        Shuffle the deck
        """
        assert len(self.cards) > 0, "Can't shuffle an empty deck"
        reShuffled = shuffle(list(self.cards))
        self.cards = deque(reShuffled)
    
    def draw(self, number: int) -> list:
        """
        Draw a number of cards from the deck
        """
        assert len(self.cards) > 0, "Can't draw from an empty deck."
        cardsDrawn: list = []
        for _ in range(number):
            cardsDrawn.append(self.cards.pop())
        return cardsDrawn
    
    def insert(self, cards: list) -> None:
        """
        Place cards into the back of the deck (input parameter must be list) (no typechecking)
        """
        assert type(cards) == list, "When inserting cards into Deck, cards must be in a list."
        for card in cards:
            self.cards.appendleft(card)

class Destination:
    """
    The object to represent a destination card in Ticket to Ride
    """
    def __init__(self, 
                 city1: str, 
                 city2: str, 
                 points: int, 
                 index: int
                 ) -> None:
        """
        Create a destination card (index denotes a constant value for this card)
        """
        self.city1: str = city1
        self.city2: str = city2
        self.points: int = points
        self.index: int = index
    
    def __str__(self) -> str:
        return f"({self.index}) {self.city1} --{self.points}-- {self.city2}"

class Route:
    """
    The object to represent a single route between two cities in Ticket to Ride
    """
    def __init__(self, 
                 city1: str, 
                 city2: str, 
                 weight: int,
                 color: str,
                 index: int
                 ) -> None:
        self.city1: str = city1
        self.city2: str = city2
        self.weight: int = weight
        self.color: str = color
        self.index: int = index
        """
        Create a Route object (index denotes constant value for Route)
        """
    
    def __str__(self) -> str:
        return f"({self.index}) {self.city1} --{self.weight}-- {self.city2} ({self.color})"

class Action:
    """
    The object representing an action to take/taken in the game
    """
    def __init__(self, action: int, route: Route = None, colorsUsed: list[str] = None, colorToDraw: str = None, askingForDeal: bool = None, takeDests: list[int] = None) -> None:
        """
        Create an action object (0 - Place Route, 1 - Draw Face Up, 2 - Draw Face Down, 3 - Draw Destination Card)

        On initialization, relevant parameters must be supplied depending on which action is being described.
        """
        self.action = action
        if self.action == 0:
            assert route != None, "Action object: route placement but route object not given"
            assert type(route) == Route, "Action object: route not supplied as type Route"
            assert colorsUsed != None, "Action object: route placement but colors used not given"
            assert len(colorsUsed) > 0, "Action object: route placement but colors used is empty"
            self.route = route
            self.colorsUsed = colorsUsed
        elif self.action == 1:
            assert colorToDraw != None, "Action object: drawing from face up but which index from face up is not supplied"
            assert type(colorToDraw) == str, "Action object: colorToDraw must be supplied as integer"
            self.colorToDraw = colorToDraw
        elif self.action == 3:
            assert askingForDeal != None, "Action object: destination deal understood but object does not know if deal was given or asked"
            self.askingForDeal = askingForDeal
            if askingForDeal == False:
                assert takeDests != None, "Action object: indicated that destinations have been dealt but no takeDest of indexes is supplied"
                assert type(takeDests) == list, "Action object: takeDests not supplied correctly, must be list of indexes"
                self.takeDests = takeDests
    
    def __str__(self) -> str:
        return f"{self.action}"

class Agent:
    """
    The agent object that plays Ticket to Ride
    """
    def __init__(self, name: str) -> None:
        """
        Initialize an agent (give it a cool name!)
        """
        self.points: int = 0
        self.name: str = name
        self.trainsLeft: int = 45
        self.turnOrder: int = None
        self.trainCards: list[str] = []
        self.destinationCards: list[Destination] = []
        self.colorCounts: list[list[str]] = [[0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0]]
        """The known cards for each other player in the game (each color its own index)"""
    
    def __str__(self) -> str:
        return f"(PLAYER {self.turnOrder}) {self.name}: {self.points} points, {self.trainsLeft} trains left\n{self.destinationCards}\n{self.trainCards}"

class Game:
    """
    The game & state representation object for Ticket to Ride
    """
    def __init__(self, 
                 map: str, 
                 players: list[Agent],
                 logs: bool,
                 draw: bool
                 ) -> None:
        """
        Initialize a game of Ticket to Ride that is ready to play.
        """
        self.map: str = map
        self.doLogs: bool = logs
        self.drawGame: bool = draw
        self.gameOver: bool = False
        self.lastTurn: bool = False
        self.endedGame: Agent = None
        self.colorPicked: str = None
        self.turn = 1 - len(players)
        self.wildPicked: bool = False
        self.gameLogs: list[str] = []
        self.trainCarDeck: Deck = trainCarDeck()
        self.destinationDeal: list[Destination] = None
        self.movePerforming: Action = Action(3, askingForDeal=True)
        self.board: nx.MultiGraph = initBoard(self.map, len(players))
        self.faceUpCards: list[str] = self.trainCarDeck.draw(5)
        self.destinationCards: list[Destination] = getDestinationCards(map)
        self.destinationsDeck: Deck[Destination] = Deck(self.destinationCards)
        self.players: list[Agent] = players if ((2 <= len(players) <= 4)) else sys.exit("ERROR: Game must have 2-4 players")
        for i, player in enumerate(self.players):
            player.turnOrder = i
            player.trainCards = self.trainCarDeck.draw(4)
        self.makingNextMove: Agent = self.players[0]

    def __str__(self) -> str:
        info = f"Turn: {self.turn}\nPlayers: {len(self.players)}\nGame Over: {self.gameOver}\nFinal Turns: {self.lastTurn}\nDestinations Left: {self.destinationsDeck.count()}\nTrain Cards Left: {self.trainCarDeck.count()}\n{self.faceUpCards}\n--------------------------------------------------\n{self.makingNextMove}"
        return info
    
    def clone(self):
        """
        Creates a deep copy of the current Game
        """
        new = Game(self.map, self.players, False, False)
        new.turn = deepcopy(self.turn)
        new.board = deepcopy(self.board)
        new.players = deepcopy(self.players)
        new.gameLogs = deepcopy(self.gameLogs)
        new.gameOver = deepcopy(self.gameOver)
        new.lastTurn = deepcopy(self.lastTurn)
        new.endedGame = deepcopy(self.endedGame)
        new.wildPicked = deepcopy(self.wildPicked)
        new.faceUpCards = deepcopy(self.faceUpCards)
        new.colorPicked = deepcopy(self.colorPicked)
        new.trainCarDeck = deepcopy(self.trainCarDeck)
        new.makingNextMove = deepcopy(self.makingNextMove)
        new.movePerforming = deepcopy(self.movePerforming)
        new.destinationDeal = deepcopy(self.destinationDeal)
        new.destinationCards = deepcopy(self.destinationCards)
        new.destinationsDeck = deepcopy(self.destinationsDeck)
        return new

    def draw(self) -> None:
        """
        Draws the graph representation of the current game using matplotlib
        """
        pos = nx.spectral_layout(self.board)
        nx.draw_networkx_nodes(self.board, pos)
        nx.draw_networkx_labels(self.board, pos, font_size=6)
        nx.draw_networkx_edges(self.board, pos)
        pyplot.show()

    def validMoves(self) -> list[Action]:
        """
        Returns a list of valid Action objects that denote the actions that can be taken form the current game state. Returns an empty list if there are no valid actions to take (i.e. game is over)
        """
        actionList: list[Action] = []
        
        if self.gameOver: return actionList
        else:
            if self.movePerforming == None:
                numWilds: int = self.makingNextMove.trainCards.count("WILD")
                for route in self.board.edges(data=True):

                    if route[2]['owner'] != '': continue
                    weight: int = int(route[2]['weight'])
                    color: str = route[2]['color']
                    routeType: Route = Route(route[0], route[1], route[2]['weight'], route[2]['color'], route[2]['index'])
                    
                    if color != "GRAY":

                        numColor: int = self.makingNextMove.trainCards.count(color)
                        if numColor == 0: continue
                        elif numColor < weight:
                            if numWilds > 0:
                                if numWilds + numColor == weight: actionList.append(Action(0, routeType, [color, 'WILD']))
                                elif numWilds + numColor > weight:
                                    actionList.append(Action(0, routeType, [color, 'WILD']))
                                    if numWilds < weight:
                                        actionList.append(Action(0, routeType, ['WILD', color]))
                        elif numColor >= weight:
                            actionList.append(Action(0, routeType, [color]))
                            if 0 < numWilds < weight:
                                actionList.append(Action(0, routeType, ['WILD', color]))
                    else:
                        for color in color_indexing.keys():

                            numColor: int = self.makingNextMove.trainCards.count(color)
                            if numColor == 0: continue
                            elif numColor < weight:
                                if numWilds > 0:
                                    if numWilds + numColor == weight: actionList.append(Action(0, routeType, [color, 'WILD']))
                                    if numWilds + numColor > weight:
                                        actionList.append(Action(0, routeType, [color, 'WILD']))
                                        if numWilds < weight:
                                            actionList.append(Action(0, routeType, ['WILD', color]))
                                else: continue
                            elif numColor >= weight:
                                actionList.append(Action(0, routeType, [color]))
                                if 0 < numWilds < weight:
                                    actionList.append(Action(0, routeType, ['WILD', color]))
                        if numWilds >= weight:
                            actionList.append(Action(0, routeType, ['WILD']))
                if len(self.faceUpCards) > 0:
                    for card in self.faceUpCards:
                        actionList.append(Action(1, colorToDraw=card))
                if self.trainCarDeck.count() > 0:
                    actionList.append(Action(2))
                if self.destinationsDeck.count() >= 3:
                    actionList.append(Action(3, askingForDeal=True))
            elif self.movePerforming.action == 1:
                for card in self.faceUpCards:
                    if card == "WILD": continue
                    else: actionList.append(Action(1, colorToDraw=card))
                if self.trainCarDeck.count() >= 1: actionList.append(Action(2))
            elif self.movePerforming.action == 2:
                for card in self.faceUpCards:
                    actionList.append(Action(1, colorToDraw=card))
                if self.trainCarDeck.count() >= 1: actionList.append(Action(2))
            elif self.movePerforming.action == 3:
                for take in listDestTakes():
                    actionList.append(Action(3, askingForDeal=False, takeDests=take))

        if len(actionList) == 0:
            self.gameOver = True
            self.endedGame = self.makingNextMove.turnOrder
            print("No valid moves found for this state. Setting game to over.")
        
        return actionList

class Node:
    """
    An object representing a node storing a game state in MCTS
    """
    def __init__(self, priorProb: float) -> None:
        self.visits: int = 0                    # N(s,a)
        self.totalWinProb: float = 0            # W(s,a)
        self.priorProb: float = priorProb       # P(s,a)
        self.children: dict[Action, Node] = {}
    
    def isExpanded(self) -> bool:
        """
        Returns true if a node has been expanded already (has children)
        """
        return len(self.children) > 0
    
    def value(self) -> float:
        """
        Get the mean action value - Q(s,a) - of the node
        """
        if self.visits == 0:
            return 0
        return self.totalWinProb / self.visits

"""
FUNCTIONS
--------------------------------------------
"""

def getDestinationCards(map: str) -> list[Destination]:
    """
    Takes a map name and returns a list of paths between cities where each item is a Destination object
    """
    lines = open(f"internal/{map}_destinations.txt").readlines()
    cards: list[Destination] = []
    index = 0
    for card in lines:
        data = re.search('(^\D+)(\d+)\s(.+)', card)
        cards.append(Destination(data.group(1).strip(), data.group(3).strip(), int(data.group(2).strip()), index))
        index += 1
    return cards

def getRoutes(map: str) -> list[Route]:
    """
    Takes a map name and returns a list of paths between cities where each item is a Route object
    """
    lines = open(f"internal/{map}_paths.txt").readlines()
    paths = []
    index = 0
    for path in lines:
        data = re.search('(^\D+)(\d)\W+(\w+)\W+(.+)', path)
        paths.append(Route(data.group(1).strip(), data.group(4).strip(), int(data.group(2).strip()), data.group(3).strip(), index))
        index += 1
    return paths

def trainCarDeck() -> Deck:
    """
    Builds the standard train car deck of 110 cards
    """
    deck = ['PINK']*12+['WHITE']*12+['BLUE']*12+['YELLOW']*12+['ORANGE']*12+['BLACK']*12+['RED']*12+['GREEN']*12+['WILD']*14
    return Deck(deck)

def initBoard(map: str, players: int) -> nx.MultiGraph:
    """
    Creates a networkx MultiGraph representation of the game board given a map name
    """
    board = nx.MultiGraph()
    if players == 4:
        board.add_edges_from((route.city1, route.city2, {'weight': route.weight, 'color': route.color, 'owner': None, 'index': route.index}) for route in getRoutes(map))
    else:
        board.add_edges_from((route.city1, route.city2, {'weight': route.weight, 'color': route.color, 'owner': None, 'index': route.index}) for route in getRoutes(map) if board.has_edge(route.city1, route.city2) == False)
    return board

def listDestTakes() -> list[list[int]]:
    return [[0], [1], [2], [0, 1], [0, 2], [1, 2], [0, 1, 2]]

"""
VARIABLES
--------------------------------------------
"""

color_indexing: dict[str, int] = {'PINK': 0, 'WHITE': 1, 'BLUE': 2, 'YELLOW': 3, 'ORANGE': 4, 'BLACK': 5, 'RED': 6, 'GREEN': 7, 'WILD': 8}
"""A dictionary that maps string names to their index values (standardization)"""