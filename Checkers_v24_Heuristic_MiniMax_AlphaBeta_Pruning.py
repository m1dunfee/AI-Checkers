from graphics import *
import sys
from tkinter import messagebox
from random import randrange

class Checkers:
    def __init__(self):
        # -------- Game State --------
        self.search_depth = 2   # never less than 1
        self.state = 'CustomSetup'
        self.is1P = False
        self.compIsColour = 'not playing'   # 'White' or 'Black' when 1P mode is on
        self.placeColour = 'White'           # for custom setup
        self.placeRank = 'Pawn'              # 'Pawn' or 'King'
        self.placeType = 'Place'             # 'Place' or 'Delete'
        self.pTurn = 'White'                 # 'White' or 'Black'

        self.selectedTileAt = []
        self.pieceCaptured = False

        self.BoardDimension = 8
        self.numPiecesAllowed = 12

        # -------- GUI Initialization --------
        self.win = GraphWin('Checkers', 600, 600)
        self.win.setBackground('White')
        self.win.setCoords(-1, -3, 11, 9)

        self.ClearBoard()

        # Create 8x8 array of Tile objects (all empty initially)
        self.tiles = [
            [Tile(self.win, i, j, False) for i in range(self.BoardDimension)]
            for j in range(self.BoardDimension)
        ]

        # These lists will be used by the engine
        self.moves = []  # holds the list of [x1, y1, x2, y2] legal moves

        # Draw row/column labels
        gridLetters = ['A','B','C','D','E','F','G','H']
        for i in range(self.BoardDimension):
            Text(Point(-0.5, i + 0.5), i + 1).draw(self.win)
            Text(Point( 8.5, i + 0.5), i + 1).draw(self.win)
            Text(Point(i + 0.5, -0.5), gridLetters[i]).draw(self.win)
            Text(Point(i + 0.5,  8.5), gridLetters[i]).draw(self.win)

        self.SetButtons()
        self.SetupBoard()

    ##########################################
    # Heuristic Implementation               #
    ##########################################
    ##########################################
    # Alpha-Beta Pruning and Move Evaluation #
    ##########################################   
    def alpha_beta(self, depth, alpha, beta, last_move=None):
        def count_all_pieces():
            return sum(tile.isPiece for row in self.tiles for tile in row)

        legal_moves = self.movesAvailable()
        print("[alpha_beta] Enter: depth={}, pieces={}".format(depth, count_all_pieces()))

        if depth == 0 or not legal_moves:
            print("[alpha_beta] Leaf/terminal: pieces={}".format(count_all_pieces()))
            if last_move is not None:
                val = self.weight_move(last_move)
                print("  [leaf] weight_move for last_move:", last_move, "=", val)
                return val
            else:
                return 0

        best_value = float('-inf')

        for move in legal_moves:
            print("  [move] Before move: pieces={}".format(count_all_pieces()))
            snapshot = self.snapshot_board()
            self.make_move(move)
            print("  [move] After move: pieces={}".format(count_all_pieces()))

            value = -self.alpha_beta(depth - 1, -beta, -alpha, move)

            # Score after move, before restore
            if depth == 1 and last_move is not None:
                print("DEBUG weight_move (before restore):", self.weight_move(move))

            self.restore_board(snapshot)
            print("  [move] After restore: pieces={}".format(count_all_pieces()))

            if value > best_value:
                best_value = value
            if best_value > alpha:
                alpha = best_value
            if alpha >= beta:
                print("  [prune] Beta cutoff at depth={}, value={}".format(depth, best_value))
                break

        print("[alpha_beta] Exit: depth={}, best_value={}, pieces={}".format(depth, best_value, count_all_pieces()))
        return best_value

    def make_move(self, move_seq):
        """
        Phase 1: slide the piece through each hop, record snaps for undo,
        and return (snaps, orig_turn) WITHOUT clearing captures here.
        """
        snaps = []
        orig_turn = self.pTurn

        for x1, y1, x2, y2 in move_seq:
            # snapshot source and dest (and captured square if any)
            snap = [
                (x1, y1, self.tiles[x1][y1]),
                (x2, y2, self.tiles[x2][y2])
            ]
            if abs(x2 - x1) == 2:
                mx, my = (x1 + x2)//2, (y1 + y2)//2
                snap.append((mx, my, self.tiles[mx][my]))
            snaps.append(snap)

            # move the piece
            moving = self.tiles[x1][y1]
            self.tiles[x2][y2] = Tile(self.win, x2, y2,
                                      True,
                                      moving.pieceColour,
                                      moving.pieceRank)
            self.tiles[x1][y1] = Tile(self.win, x1, y1, False)

            # **DO NOT** clear the captured tile here!

        # flip turn last
        self.pTurn = self.opposite(self.pTurn)
        return snaps, orig_turn

    def finalize_move(self, move_result):
        """
        Phase 2: given (snaps, orig_turn), clear each jumped square.
        """
        snaps, _ = move_result
        for snap in snaps:
            # snap == [(x1,y1,t), (x2,y2,t)] or 3-tuple with (mx,my,t)
            if len(snap) == 3:
                mx, my, _ = snap[2]
                self.tiles[mx][my] = Tile(self.win, mx, my, False)



    ##########################################
    # Move Scoring and Heuristic Evaluation  #
    ##########################################
    def weight_move(self, move_seq):
        """
        Heuristic: now that captures are still on board, we can score them.
        """
        BACK_ROW            = 30
        MOBILITY            = 10
        PROMOTION           = 150
        CAPTURE_KING        = 200
        CAPTURE_PAWN        = 50
        SAFETY              = 25

        # first hop gives us src; last hop gives us dst
        src_x, src_y, _, _ = (*move_seq[0],)  # unpack 4-tuple
        last_hop = move_seq[-1]
        dst_x, dst_y      = last_hop[2], last_hop[3]

        # capture the mover’s color
        mover = self.tiles[src_x][src_y]
        color = mover.pieceColour

        score = 0

        # BACK_ROW
        if self.movesFromBack([src_x, src_y, dst_x, dst_y]):
            score += BACK_ROW

        # MOBILITY
        if not self.PieceCanCapture(dst_x, dst_y):
            score += MOBILITY

        # PROMOTION
        dest = self.tiles[dst_x][dst_y]
        if (dest.isPawn and
            ((dst_y == 7 and color == 'White') or
             (dst_y == 0 and color == 'Black'))):
            score += PROMOTION

        # CAPTURE bonuses
        for x1, y1, x2, y2 in move_seq:
            if abs(x2 - x1) == 2:
                mx, my = (x1 + x2)//2, (y1 + y2)//2
                cap = self.tiles[mx][my]
                if cap.isKing:
                    score += CAPTURE_KING
                elif cap.isPawn:
                    score += CAPTURE_PAWN

        # SAFETY
        if self.isMoveSafe([src_x, src_y, dst_x, dst_y]):
            score += SAFETY

        return score

    ##########################################
    # Multi-Jump Capture Logic               #
    ##########################################
    def getCaptureSequences(self, x, y, path=None, visited=None):
        """
        Recursively finds all legal multi-jump sequences for the piece at (x, y).
        Each result is a list of [x1, y1, x2, y2] hops in order.
        """
        if path is None:
            path = []
        if visited is None:
            visited = set()
        sequences = []
        found = False

        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            mid_x, mid_y = x + dx, y + dy
            end_x, end_y = x + 2 * dx, y + 2 * dy

            if (0 <= mid_x < 8 and 0 <= mid_y < 8 and
                0 <= end_x < 8 and 0 <= end_y < 8 and
                self.tiles[x][y].isPiece and
                self.tiles[x][y].pieceColour == self.pTurn and
                self.tiles[mid_x][mid_y].isPiece and
                self.tiles[mid_x][mid_y].pieceColour == self.opposite(self.pTurn) and
                not self.tiles[end_x][end_y].isPiece and
                (mid_x, mid_y, end_x, end_y) not in visited):

                found = True
                # Save board state to restore after recursion
                snap = [
                    (x, y, self.tiles[x][y]),
                    (mid_x, mid_y, self.tiles[mid_x][mid_y]),
                    (end_x, end_y, self.tiles[end_x][end_y])
                ]
                # Perform jump: move to end, remove captured, clear source
                self.tiles[end_x][end_y] = Tile(self.win, end_x, end_y, True,
                                                self.tiles[x][y].pieceColour,
                                                self.tiles[x][y].pieceRank)
                self.tiles[x][y] = Tile(self.win, x, y, False)
                self.tiles[mid_x][mid_y] = Tile(self.win, mid_x, mid_y, False)
                # Optional: Promote if you want forced kinging during a chain

                new_path = path + [[x, y, end_x, end_y]]
                new_visited = visited | {(mid_x, mid_y, end_x, end_y)}
                # Recurse for further jumps from the new position
                further = self.getCaptureSequences(end_x, end_y, new_path, new_visited)
                if further:
                    sequences.extend(further)
                else:
                    sequences.append(new_path)
                # Restore board
                for rx, ry, tile in snap:
                    self.tiles[rx][ry] = tile

        if not found and path:
            # No further jumps, return the accumulated path if at least one jump occurred
            sequences.append(path)
        return sequences

    ##########################################
    # Board State Management                 #
    ##########################################
    def snapshot_board(self):
        return (
            [[(tile.isPiece, tile.pieceColour, tile.pieceRank) for tile in row] for row in self.tiles],
            self.pTurn
        )


    def restore_board(self, snapshot):
        board_state, turn = snapshot
        for x in range(8):
            for y in range(8):
                isPiece, pieceColour, pieceRank = board_state[x][y]
                self.tiles[x][y] = Tile(self.win, x, y, isPiece, pieceColour, pieceRank)
        self.pTurn = turn

    ##########################################
    # Heuristic Implementation end           #
    ##########################################

    def CompTurn(self):
        import math

        depth       = self.search_depth
        legal_moves = self.movesAvailable()
        if not legal_moves:
            return

        best_score = -math.inf
        best_move  = None

        for move in legal_moves:
            # 1) Snapshot current board & turn
            snapshot = self.snapshot_board()

            # 2) Phase 1: apply move (captures still on board)
            snaps, orig_turn = self.make_move(move)

            # 3) Score immediate gain (captures still present)
            gain = self.weight_move(move)

            # 4) Phase 2: clear the captured pieces
            self.finalize_move((snaps, orig_turn))

            # 5) Evaluate opponent’s best reply
            reply_penalty = -self.alpha_beta(
                depth - 1,
                float('-inf'),
                float('inf'),
                None
            )

            # 6) Restore full board & turn for next trial
            self.restore_board(snapshot)

            # 7) Combine your gain with their reply “penalty”
            total = gain + reply_penalty
            if total > best_score:
                best_score = total
                best_move  = move

        # 8) Execute the chosen move for real, same two-phase:
        if best_move:
            snaps, orig_turn = self.make_move(best_move)
            self.finalize_move((snaps, orig_turn))

    #
    # 7) hasMorePieces(): True if side-to-move has more total pieces than opponent.
    #
    def hasMorePieces(self):
        return self.numColour(self.pTurn) > self.numColour(self.opposite(self.pTurn))


    #
    # ----- Original Heuristic Helpers (unchanged) -----
    #

    def isMoveSafe(self, move):
        """
        Returns True if, after executing this move, the moved piece cannot be immediately captured.
        """
        endx, endy = self.moveEndsAt(move)
        X1 = [endx - 1, endx + 1]
        Y1 = [endy - 1, endy + 1]
        for i in range(2):
            for j in range(2):
                if self.SpecialPCCP(
                    self.tiles[move[0]][move[1]].pieceColour,
                    X1[i], Y1[j],
                    endx, endy,
                    move[0], move[1]
                ):
                    return False
        return True


    def SpecialPCCP(self, piece2Colour, x, y, X, Y, initX, initY):
        """
        Modified PieceCanCapturePiece that checks if an enemy at (x,y) can capture
        the moving piece at (X,Y), ignoring the mover's original square.
        """
        X1 = [x - 1, x + 1]
        X2 = [x - 2, x + 2]
        Y1 = [y - 1, y + 1]
        Y2 = [y - 2, y + 2]

        if not ((0 <= X < 8) and (0 <= Y < 8) and (0 <= x < 8) and (0 <= y < 8)):
            return False
        if piece2Colour != self.opposite(self.tiles[x][y].pieceColour):
            return False
        if not self.CanDoWalk(x, y, X, Y, exception=False):
            return False

        for i in range(2):
            for j in range(2):
                if X1[i] == X and Y1[j] == Y:
                    if (0 <= X2[i] < 8) and (0 <= Y2[j] < 8):
                        if (not self.tiles[X2[i]][Y2[j]].isPiece) or (X2[i] == initX and Y2[j] == initY):
                            return True
        return False


    def movesFromBack(self, move):
        """
        Return True if the source square is on the back row for compIsColour.
        """
        src_x, src_y = move[0], move[1]
        if (src_y == 0 and self.compIsColour == 'White') or \
           (src_y == 7 and self.compIsColour == 'Black'):
            return True
        return False


    def moveEndsAt(self, move):
        """
        Given [x1,y1,x2,y2], return the actual landing square [endx, endy],
        accounting for a jump if (x2,y2) is occupied.
        """
        x1, y1, x2, y2 = move
        if self.tiles[x2][y2].isPiece:
            return [x1 + (x2 - x1) * 2, y1 + (y2 - y1) * 2]
        return [x2, y2]


    def movesAvailable(self):
        all_caps = []
        for x in range(8):
            for y in range(8):
                if self.tiles[x][y].isPiece and self.tiles[x][y].pieceColour == self.pTurn:
                    caps = self.getCaptureSequences(x, y)
                    if caps:
                        all_caps.extend(caps)
        if all_caps:
            return all_caps  # Only capturing moves when any exist
        # If no captures, return normal moves as before:
        moves = []
        for x in range(8):
            for y in range(8):
                if self.tiles[x][y].isPiece and self.tiles[x][y].pieceColour == self.pTurn:
                    X1 = [x - 1, x + 1]
                    Y1 = [y - 1, y + 1]
                    for i in range(2):
                        for j in range(2):
                            x2, y2 = X1[i], Y1[j]
                            if 0 <= x2 < 8 and 0 <= y2 < 8:
                                if self.moveIsValid(x, y, x2, y2):
                                    moves.append([[x, y, x2, y2]])  # Single move as a list for consistency
        return moves



    # ----- GUI and Game-Play Code (mostly unchanged) -----

    def SetupBoard(self):
        while self.state == 'CustomSetup':
            self.Click()
        if self.state == 'Play':
            self.Play()


    def Play(self):
        while self.state == 'Play':
            if self.is1P and self.compIsColour == self.pTurn:
                self.CompTurn()
            else:
                self.Click()
        if self.state == 'CustomSetup':
            self.SetupBoard()


    def ClearBoard(self):
        """
        Reset the board to empty and switch to CustomSetup mode.
        """
        self.tiles = [
            [Tile(self.win, i, j, False) for i in range(self.BoardDimension)]
            for j in range(self.BoardDimension)
        ]
        for i in range(self.BoardDimension):
            for j in range(self.BoardDimension):
                self.ColourButton(self.TileColour(i, j), i, j)
        self.state = 'CustomSetup'
        self.pTurn = 'White'
        self.SetButtons()


    def ColourButton(self, colour, X, Y, width=1, height=1):
        rect = Rectangle(Point(X, Y), Point(X + width, Y + height))
        rect.setFill(colour)
        rect.draw(self.win)


    def TileColour(self, x, y):
        if (x % 2 == 0 and y % 2 == 0) or (x % 2 == 1 and y % 2 == 1):
            return 'Red'
        return 'White'


    ##########
    # Draw control buttons along top/bottom
    ##########
    def SetButtons(self):
        self.ColourButton('White', -1, -3, 12, 2)
        self.ColourButton('White',  9, -1,  2, 10)

        if self.state == 'CustomSetup':
            self.DrawStandard()
            self.DrawStart()
            self.DrawClear()
            self.Draw1P()
            self.Draw2P()
            self.DrawLoad()
            self.DrawSave()
            self.DrawTurn()
            self.DrawX()

            self.DrawW()
            self.DrawB()
            self.DrawK()
            self.DrawDel()

            self.DrawScore()
        elif self.state == 'Play':
            self.DrawResign()
            self.DrawSave()
            self.DrawTurn()
            self.DrawX()
            self.DrawScore()


    def DrawStandard(self):
        self.ColourButton('White', -1, -2, 2, 1)
        Text(Point(0, -1.3), 'Standard').draw(self.win)
        Text(Point(0, -1.7), 'Setup').draw(self.win)

    def DrawCustom(self):
        self.ColourButton('White', -1, -3, 2, 1)
        Text(Point(0, -2.3), 'Custom').draw(self.win)
        Text(Point(0, -2.7), 'Setup').draw(self.win)

    def DrawStart(self):
        self.ColourButton('Yellow', 1, -2)
        Text(Point(1.5, -1.5), 'Start!').draw(self.win)

    def DrawClear(self):
        self.ColourButton('White', -1, -3, 2, 1)
        Text(Point(0, -2.3), 'Clear').draw(self.win)
        Text(Point(0, -2.7), 'Board').draw(self.win)

    def Draw1P(self):
        col = 'Red'
        if self.is1P:
            self.DrawCompColour()
        else:
            self.ColourButton(col, 3, -2, 2, 1)
            Text(Point(4, -1.3), '1Player').draw(self.win)
            Text(Point(4, -1.7), 'Game').draw(self.win)

    def DrawCompColour(self):
        self.ColourButton(self.compIsColour, 3, -2, 2, 1)
        txt1 = Text(Point(4, -1.3), 'Comp Is')
        txt2 = Text(Point(4, -1.7), self.compIsColour)
        txt1.draw(self.win)
        txt2.draw(self.win)
        txt1.setFill(self.opposite(self.compIsColour))
        txt2.setFill(self.opposite(self.compIsColour))

    def Draw2P(self):
        col = 'Green'
        if self.is1P:
            col = 'Red'
        self.ColourButton(col, 3, -3, 2, 1)
        Text(Point(4, -2.3), '2Player').draw(self.win)
        Text(Point(4, -2.7), 'Game').draw(self.win)

    def DrawLoad(self):
        self.ColourButton('White', 6, -3, 2, 1)
        Text(Point(7, -2.5), 'Load').draw(self.win)

    def DrawSave(self):
        self.ColourButton('White', 8, -3, 2, 1)
        Text(Point(9, -2.5), 'Save').draw(self.win)

    def DrawX(self):
        self.ColourButton('Red', 10, -3)
        Exit_txt = Text(Point(10.5, -2.5), 'X')
        Exit_txt.draw(self.win)
        Exit_txt.setFill('White')

    def DrawW(self):
        col = 'Green'
        if self.placeColour != 'White':
            col = 'Red'
        self.ColourButton(col, 6, -2)
        Text(Point(6.5, -1.5), 'W').draw(self.win)

    def DrawB(self):
        col = 'Red'
        if self.placeColour != 'White':
            col = 'Green'
        self.ColourButton(col, 7, -2)
        Text(Point(7.5, -1.5), 'B').draw(self.win)

    def DrawK(self):
        col = 'Red'
        if self.placeRank == 'King':
            col = 'Green'
        self.ColourButton(col, 8, -2)
        Text(Point(8.5, -1.5), 'K').draw(self.win)

    def DrawDel(self):
        col1 = 'Black'
        col2 = 'White'
        if self.placeType == 'Delete':
            col1 = 'Green'
            col2 = 'Black'
        self.ColourButton(col1, 9, -2)
        deleteTxt = Text(Point(9.5, -1.5), 'Del')
        deleteTxt.draw(self.win)
        deleteTxt.setFill(col2)

    def DrawResign(self):
        self.ColourButton('White', 6, -3, 2, 1)
        Text(Point(7, -2.5), 'Resign').draw(self.win)

    def DrawTurn(self):
        col1 = 'White'
        col2 = 'Black'
        if self.pTurn == 'Black':
            col1 = 'Black'
            col2 = 'White'
        self.ColourButton(col1, 9, 8, 2, 1)
        txt1 = Text(Point(10, 8.7), col1)
        txt2 = Text(Point(10, 8.3), 'Turn')
        txt1.draw(self.win)
        txt2.draw(self.win)
        txt1.setFill(col2)
        txt2.setFill(col2)

    def DrawScore(self):
        Text(Point(10, 7.5), '# White').draw(self.win)
        Text(Point(10, 7.1), 'Pieces:').draw(self.win)
        Text(Point(10, 6.7), self.numColour('White')).draw(self.win)
        Text(Point(10, 5.9), '# Black').draw(self.win)
        Text(Point(10, 5.5), 'Pieces').draw(self.win)
        Text(Point(10, 5.1), self.numColour('Black')).draw(self.win)


    def Click(self):
        click = self.win.getMouse()
        X, Y = self.ClickedSquare(click)
        self.Action(X, Y)


    def Action(self, X, Y):
        if self.state == 'CustomSetup':
            self.clickInCustom(X, Y)
        elif self.state == 'Play':
            self.clickInPlay(X, Y)


    def clickInCustom(self, X, Y):
        # X button
        if (10 <= X < 11 and -3 <= Y < -2):
            ExitGame(self.win)

        # Standard Setup
        elif (-1 <= X < 1 and -2 <= Y < -1):
            self.StandardSetup()

        # Start! button
        elif (1 <= X < 2 and -2 <= Y < -1):
            num_wh = self.numColour('White')
            num_bl = self.numColour('Black')
            if (num_wh == 0 and num_bl == 0):
                messagebox.showinfo("Error", "No pieces have been placed!")
            else:
                self.state = 'Play'
                self.SetButtons()

        # Clear Board
        elif (-1 <= X < 1 and -3 <= Y < -2):
            self.ClearBoard()

        # 1Player / Comp Is
        elif (3 <= X < 5 and -2 <= Y < -1 and not self.is1P):
            self.is1P = True
            self.compIsColour = 'White'
            self.SetButtons()
        elif (3 <= X < 5 and -2 <= Y < -1 and self.is1P):
            self.compIsColour = self.opposite(self.compIsColour)
            self.SetButtons()

        # 2Player
        elif (3 <= X < 5 and -3 <= Y < -2):
            self.is1P = False
            self.SetButtons()

        # Save / Load
        elif (8 <= X < 10 and -3 <= Y < -2):
            self.SaveSetupToFile()
        elif (6 <= X < 8 and -3 <= Y < -2):
            self.LoadSetupFromFile()

        # pTurn toggle
        elif (9 <= X < 11 and 8 <= Y < 9):
            self.pTurn = self.opposite(self.pTurn)
            self.SetButtons()

        # Choose color/rank/delete in CustomSetup
        elif (6 <= X < 7 and -2 <= Y < -1):
            self.placeColour = 'White'
            self.placeType = 'Place'
            self.SetButtons()
        elif (7 <= X < 8 and -2 <= Y < -1):
            self.placeColour = 'Black'
            self.placeType = 'Place'
            self.SetButtons()
        elif (8 <= X < 9 and -2 <= Y < -1):
            self.placeRank = self.opposite(self.placeRank)
            self.placeType = 'Place'
            self.SetButtons()
        elif (9 <= X < 10 and -2 <= Y < -1):
            self.placeType = self.opposite(self.placeType)
            self.SetButtons()

        # Place/Delete a piece on the board
        elif (0 <= X < 8 and 0 <= Y < 8):
            if self.tiles[X][Y].TileColour(X, Y) == 'White':
                messagebox.showinfo("Error", "Illegal Placement")
            elif self.numColour(self.placeColour) >= self.numPiecesAllowed and self.placeType == 'Place':
                messagebox.showinfo("Error", "Illegal Placement")
            elif ((Y == 7 and self.placeColour == 'White' and not (self.placeRank == 'King')) or
                  (Y == 0 and self.placeColour == 'Black' and not (self.placeRank == 'King'))):
                messagebox.showinfo("Error", "Illegal Placement")
            else:
                self.tiles[X][Y] = Tile(self.win, X, Y, self.placeType == 'Place',
                                        self.placeColour, self.placeRank)
                self.SetButtons()


    def clickInPlay(self, X, Y):
        # X button
        if (10 <= X < 11 and -3 <= Y < -2):
            ExitGame(self.win)

        # Save
        elif (8 <= X < 10 and -3 <= Y < -2):
            self.SaveSetupToFile()

        # Resign
        elif (6 <= X < 8 and -3 <= Y < -2):
            messagebox.showinfo("Resignation",
                                  str(self.pTurn) + ' has resigned! ' +
                                  str(self.opposite(self.pTurn)) + ' wins!')
            self.state = 'CustomSetup'
            self.SetButtons()

        # Tile clicked in Play
        elif (0 <= X < 8 and 0 <= Y < 8):
            if self.selectedTileAt:
                # Re-selecting same piece to deselect
                if (self.selectedTileAt[0] == X and self.selectedTileAt[1] == Y and not self.pieceCaptured):
                    self.selectedTileAt = []
                    self.tiles[X][Y] = Tile(self.win, X, Y,
                                            self.tiles[X][Y].isPiece,
                                            self.tiles[X][Y].pieceColour,
                                            self.tiles[X][Y].pieceRank)
                # Selecting a piece if it belongs to current player and can capture or no capture forced
                elif (self.pTurn == self.tiles[X][Y].pieceColour and not self.pieceCaptured and
                      (self.PieceCanCapture(X, Y) or not self.PlayerCanCapture())):
                    sx, sy = self.selectedTileAt
                    self.tiles[sx][sy] = Tile(self.win, sx, sy,
                                              self.tiles[sx][sy].isPiece,
                                              self.tiles[sx][sy].pieceColour,
                                              self.tiles[sx][sy].pieceRank)
                    self.selectedTileAt = [X, Y]
                    self.tiles[X][Y] = Tile(self.win, X, Y,
                                            self.tiles[X][Y].isPiece,
                                            self.tiles[X][Y].pieceColour,
                                            self.tiles[X][Y].pieceRank,
                                            isSelected=True)
                # Attempt a move
                elif self.moveIsValid(self.selectedTileAt[0], self.selectedTileAt[1], X, Y):
                    # If capturing a piece, adjust X,Y to actual landing square
                    if self.tiles[X][Y].isPiece:
                        X = X + (X - self.selectedTileAt[0])
                        Y = Y + (Y - self.selectedTileAt[1])
                    self.move(self.selectedTileAt[0], self.selectedTileAt[1], X, Y)
                    if not (self.pieceCaptured and self.PieceCanCapture(X, Y)):
                        self.pieceCaptured = False
                        self.selectedTileAt = []
                        self.pTurn = self.opposite(self.pTurn)
                        self.SetButtons()
                        # Check for defeat if opponent has no moves
                        if not self.movesAvailable() and self.numColour(self.pTurn):
                            messagebox.showinfo("Defeat",
                                                  str(self.pTurn) + ' has no available moves! ' +
                                                  str(self.opposite(self.pTurn)) + ' wins!')
                            self.state = 'CustomSetup'
                            self.SetButtons()
                else:
                    messagebox.showinfo("Error", "Cannot perform that action.")
            else:
                # Select a piece to move
                if self.pTurn != self.tiles[X][Y].pieceColour:
                    messagebox.showinfo("Error", "Select a piece of current player's colour")
                elif not self.PieceCanCapture(X, Y) and self.PlayerCanCapture():
                    messagebox.showinfo("Error", "Invalid selection, current player must take a piece")
                else:
                    self.selectedTileAt = [X, Y]
                    self.tiles[X][Y] = Tile(self.win, X, Y,
                                            self.tiles[X][Y].isPiece,
                                            self.tiles[X][Y].pieceColour,
                                            self.tiles[X][Y].pieceRank,
                                            isSelected=True)


    def validTileSelect(self, X, Y):
        if 0 <= X < 8 and 0 <= Y < 8:
            if self.selectedTileAt:
                sx, sy = self.selectedTileAt
                if (sx == X and sy == Y and not self.pieceCaptured):
                    return False
                elif (self.pTurn == self.tiles[X][Y].pieceColour and not self.pieceCaptured and
                      (self.PieceCanCapture(X, Y) or not self.PlayerCanCapture())):
                    return True
                elif self.moveIsValid(sx, sy, X, Y):
                    return False
                else:
                    return False
            else:
                if self.pTurn != self.tiles[X][Y].pieceColour:
                    return False
                elif not self.PieceCanCapture(X, Y) and self.PlayerCanCapture():
                    return False
                else:
                    return True
        return False


    def validTileMove(self, X, Y):
        if 0 <= X < 8 and 0 <= Y < 8:
            if self.selectedTileAt:
                sx, sy = self.selectedTileAt
                if (sx == X and sy == Y and not self.pieceCaptured):
                    return False
                elif (self.pTurn == self.tiles[X][Y].pieceColour and not self.pieceCaptured and
                      (self.PieceCanCapture(X, Y) or not self.PlayerCanCapture())):
                    return False
                elif self.moveIsValid(sx, sy, X, Y):
                    return True
                else:
                    return False
            return False
        return False


    def moveIsValid(self, x, y, X, Y):
        """
        Return True if piece at (x,y) can move to (X,Y). Checks:
          - Jump over opponent at (X,Y)
          - Or a normal diagonal move if no capture is forced.
        """
        if self.tiles[x][y].pieceColour != self.pTurn:
            return False

        if self.tiles[X][Y].pieceColour == self.opposite(self.pTurn):
            return self.PieceCanCapturePiece(x, y, X, Y)
        elif self.PieceCanJumpTo(x, y, X, Y):
            return True
        elif self.CanDoWalk(x, y, X, Y) and not self.PlayerCanCapture():
            return True
        return False


    def move(self, x, y, X, Y):
        """
        Move the piece from (x,y) to (X,Y). Handle capturing, promotion, multi-jumps.
        """
        colour = self.tiles[x][y].pieceColour
        rank   = self.tiles[x][y].pieceRank

        # Place piece at destination
        if (colour == 'White' and Y == 7) or (colour == 'Black' and Y == 0):
            rank = 'King'
        self.tiles[X][Y] = Tile(self.win, X, Y, True, colour, rank)

        # Clear source
        self.tiles[x][y] = Tile(self.win, x, y, False)

        # If jump, remove captured piece
        if abs(X - x) == 2:
            midx = x + (X - x) // 2
            midy = y + (Y - y) // 2
            if self.numColour(self.tiles[midx][midy].pieceColour) == 1:
                messagebox.showinfo("Winner",
                                      str(self.tiles[X][Y].pieceColour) + ' Wins!')
                self.state = 'CustomSetup'
                self.SetButtons()
            self.tiles[midx][midy] = Tile(self.win, midx, midy, False)

            self.tiles[X][Y] = Tile(self.win, X, Y,
                                    True,
                                    self.tiles[X][Y].pieceColour,
                                    self.tiles[X][Y].pieceRank)
            if self.PieceCanCapture(X, Y):
                self.tiles[X][Y] = Tile(self.win, X, Y,
                                        True,
                                        self.tiles[X][Y].pieceColour,
                                        self.tiles[X][Y].pieceRank,
                                        isSelected=True)
            self.selectedTileAt = [X, Y]
            self.pieceCaptured = True
        else:
            self.selectedTileAt = []
            self.tiles[X][Y] = Tile(self.win, X, Y,
                                    True,
                                    self.tiles[X][Y].pieceColour,
                                    self.tiles[X][Y].pieceRank)
            self.pieceCaptured = False


    def PlayerCanCapture(self):
        for i in range(self.BoardDimension):
            for j in range(self.BoardDimension):
                if self.pTurn == self.tiles[i][j].pieceColour:
                    if self.PieceCanCapture(i, j):
                        return True
        return False


    def PieceCanCapture(self, x, y):
        X1 = [x - 1, x + 1]
        Y1 = [y - 1, y + 1]
        for i in range(2):
            for j in range(2):
                if self.PieceCanCapturePiece(x, y, X1[i], Y1[j]):
                    return True
        return False


    def PieceCanCapturePiece(self, x, y, X, Y):
        """
        Return True if piece at (x,y) can capture opponent at (X,Y).
        """
        X1 = [x - 1, x + 1]
        X2 = [x - 2, x + 2]
        Y1 = [y - 1, y + 1]
        Y2 = [y - 2, y + 2]

        if not ((0 <= X < 8) and (0 <= Y < 8) and (0 <= x < 8) and (0 <= y < 8)):
            return False
        if self.tiles[x][y].pieceColour != self.pTurn:
            return False
        if self.tiles[X][Y].pieceColour != self.opposite(self.pTurn):
            return False
        if not self.CanDoWalk(x, y, X, Y, exception=True):
            return False

        for i in range(2):
            for j in range(2):
                if X1[i] == X and Y1[j] == Y:
                    if (0 <= X2[i] < 8) and (0 <= Y2[j] < 8):
                        if not self.tiles[X2[i]][Y2[j]].isPiece:
                            return True
        return False


    def PieceCanJumpTo(self, x, y, X, Y):
        """
        Return True if piece at (x,y) can jump to (X,Y).
        """
        X1 = [x - 1, x + 1]
        X2 = [x - 2, x + 2]
        Y1 = [y - 1, y + 1]
        Y2 = [y - 2, y + 2]
        for i in range(2):
            for j in range(2):
                if X2[i] == X and Y2[j] == Y:
                    if self.PieceCanCapturePiece(x, y, X1[i], Y1[j]):
                        return True
        return False


    def CanDoWalk(self, x, y, X, Y, exception=False):
        """
        Return True if piece at (x,y) can walk (non-capture) to (X,Y).
        Pawns move forward diagonally; kings move both directions diagonally.
        'exception' allows capture checks to invoke this as well.
        """
        X1 = [x - 1, x + 1]
        Y1 = [y - 1, y + 1]

        for i in range(2):
            for j in range(2):
                if X1[i] == X and Y1[j] == Y:
                    if (0 <= X < 8) and (0 <= Y < 8):
                        if ((self.tiles[x][y].isWhite and j == 1) or
                            (self.tiles[x][y].isBlack and j == 0) or
                            (self.tiles[x][y].isKing)):
                            if not (exception or self.tiles[X][Y].isPiece) or \
                               (exception and self.tiles[X][Y].isPiece and
                                (self.pTurn != self.tiles[X][Y].pieceColour)):
                                return True
        return False


    def StandardSetup(self):
        """
        Place pieces in the standard starting positions.
        """
        self.ClearBoard()
        self.state = 'CustomSetup'
        for i in range(self.BoardDimension):
            for j in range(self.BoardDimension):
                if self.TileColour(i, j) == 'Red' and (j < 3):
                    self.tiles[i][j] = Tile(self.win, i, j, True, 'White', 'Pawn')
                if self.TileColour(i, j) == 'Red' and (j > 4):
                    self.tiles[i][j] = Tile(self.win, i, j, True, 'Black', 'Pawn')


    def numColour(self, colour):
        """
        Count how many pieces of the given colour are on board.
        """
        c = 0
        for i in range(self.BoardDimension):
            for j in range(self.BoardDimension):
                if colour == 'White' and self.tiles[i][j].isWhite:
                    c += 1
                elif colour == 'Black' and self.tiles[i][j].isBlack:
                    c += 1
        return c


    def opposite(self, opp):
        """
        Return the "opposite" for toggles: White<->Black, King<->Pawn, Place<->Delete.
        """
        if opp == 'White':
            return 'Black'
        elif opp == 'Black':
            return 'White'
        elif opp == 'King':
            return 'Pawn'
        elif opp == 'Pawn':
            return 'King'
        elif opp == 'Place':
            return 'Delete'
        elif opp == 'Delete':
            return 'Place'
        return opp


    def ClickedSquare(self, click):
        """
        Convert a mouse-click Point into board coordinates (X, Y).
        """
        try:
            clickX = click.getX()
            clickY = click.getY()
            if clickX < 0:
                clickX = int(clickX) - 1
            else:
                clickX = int(clickX)
            if clickY < 0:
                clickY = int(clickY) - 1
            else:
                clickY = int(clickY)
            return clickX, clickY
        except IndexError:
            return self.ClickedSquare(self.win.getMouse())


    #
    # Save/Load to file (Requirement 1.6)
    #
    def SaveSetupToFile(self):
        saveFile = open('checkers.txt', 'w')
        for i in range(self.BoardDimension):
            for j in range(self.BoardDimension):
                if self.tiles[i][j].isPiece:
                    i_str = str(i)
                    j_str = str(j)
                    saveFile.write(
                        i_str + j_str +
                        str(self.tiles[i][j].pieceColour)[0] +
                        str(self.tiles[i][j].pieceRank)[0] + "\n"
                    )
        saveFile.write(self.pTurn[0])
        messagebox.showinfo("Saved Complete", "Game setup was saved to checkers.txt")
        saveFile.close()


    def LoadSetupFromFile(self):
        loadFile = open('checkers.txt', 'r')
        piece_list = loadFile.readlines()
        messagebox.showinfo("Loading", "Will now clear the board and \nplace the saved setup")
        self.ClearBoard()
        for i in range(len(piece_list) - 1):
            tot_string = piece_list[i].strip()
            x_var = int(tot_string[0])
            y_var = int(tot_string[1])
            colour_char = tot_string[2]
            rank_char = tot_string[3]
            if colour_char == 'W':
                if rank_char == 'K':
                    self.tiles[x_var][y_var] = Tile(self.win, x_var, y_var, True, 'White', 'King')
                else:
                    self.tiles[x_var][y_var] = Tile(self.win, x_var, y_var, True, 'White', 'Pawn')
            else:
                if rank_char == 'K':
                    self.tiles[x_var][y_var] = Tile(self.win, x_var, y_var, True, 'Black', 'King')
                else:
                    self.tiles[x_var][y_var] = Tile(self.win, x_var, y_var, True, 'Black', 'Pawn')
        if piece_list[-1].strip() == 'W':
            self.pTurn = 'White'
        else:
            self.pTurn = 'Black'
        self.SetButtons()
        loadFile.close()


# -----------------------------------
# Tile class (holds state of one square)
# -----------------------------------
class Tile:
    def __init__(self, win, X, Y, isPiece, pieceColour='', pieceRank='', isSelected=False):
        self.win = win
        self.x = X
        self.y = Y
        self.isPiece = isPiece
        self.isWhite = (pieceColour == 'White') and isPiece
        self.isBlack = (pieceColour == 'Black') and isPiece
        self.isKing  = (pieceRank == 'King') and isPiece
        self.isPawn  = (pieceRank == 'Pawn') and isPiece

        self.pieceColour = ''
        self.pieceRank   = ''
        if self.isWhite:
            self.pieceColour = 'White'
        elif self.isBlack:
            self.pieceColour = 'Black'
        if self.isKing:
            self.pieceRank = 'King'
        elif self.isPawn:
            self.pieceRank = 'Pawn'

        self.c = Point(self.x + 0.5, self.y + 0.5)
        self.circ = Circle(self.c, 0.4)

        if isSelected:
            self.circ.setOutline('Yellow')
        else:
            self.circ.setOutline('Black')
            self.circ.undraw()

        self.kingTxt = Text(self.c, 'K')
        self.kingTxt.undraw()

        self.ColourButton(self.TileColour(self.x, self.y), self.x, self.y)
        if self.isPiece:
            self.DrawPiece()


    def ColourButton(self, colour, X, Y, width=1, height=1):
        rect = Rectangle(Point(X, Y), Point(X + width, Y + height))
        rect.setFill(colour)
        rect.draw(self.win)


    def TileColour(self, x, y):
        if (x % 2 == 0 and y % 2 == 0) or (x % 2 == 1 and y % 2 == 1):
            return 'Red'
        return 'White'


    def DrawPiece(self):
        self.circ.draw(self.win)
        col1 = 'White' if self.isWhite else 'Black'
        col2 = 'Black' if self.isWhite else 'White'
        self.circ.setFill(col1)
        if self.isKing:
            self.kingTxt.draw(self.win)
            self.kingTxt.setFill(col2)


def ExitGame(win):
    win.close()
    sys.exit()


# Instantiate and run
game = Checkers()