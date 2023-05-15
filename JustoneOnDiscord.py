
import random
from enum import Enum, auto

import discord
from discord import TextChannel, Message, RawReactionActionEvent

# お題の入っているファイルパス
OdaiFilePath = "C:\python\justonediscord\justoneOdai.txt"

EMOJI_CHECK = '✅'
EMOJI_OK = '⭕'
EMOJI_NG = '❌'
EMOJI_DOKURO = '☠'

# ユーザーIDからメンション用文字列を作る関数
def Mention(u_id):
    return '<@' + str(u_id) + '>'

# お題管理クラス
class odaiManager:
    odaiList = []
    odaiLength = 0

    def alignLength(self, text : str):
        return text + '　' * (self.odaiLength - len(text))

    # お題ファイル読み込み関数
    def readOdai(self):
        odaiFile = open(OdaiFilePath, 'r', encoding="utf-8")
        if not odaiFile:
            print('お題ファイルが見つかりませんでした')
            self.odaiList.append('error')
            return
        odaiList = [str.rstrip('\n') for str in odaiFile.readlines()]
        # 長さを揃える
        self.odaiLength = 0
        for odai in odaiList:
            if len(odai) > self.odaiLength: self.odaiLength = len(odai)
        odaiList = [self.alignLength(odai) for odai in odaiList if odai != '']
        random.shuffle(odaiList)
        self.odaiList = odaiList
        print('お題ファイルの読み込み完了:' + str(len(odaiList)) + '単語')

    def __init__(self):
        self.readOdai()

    def GetOdai(self):
        if not self.odaiList:
            self.readOdai()
        odai = self.odaiList.pop()
        print('お題出力')
        return odai

# ゲーム進行状態
class State(Enum):
    WAITING = auto()        #ゲーム開始待機
    ENTRY = auto()          #参加
    ENTRYCHECK = auto()     #参加確認
    WAITPROPOSING = auto()  #ヒント待機
    CHECKPROPOSING = auto() #ヒント確認
    WAITANSWER = auto()     #回答待機
    CHECKANSWER = auto()    #回答確認

# ゲーム進行を管理する変数群
class justoneManager:
    def initGame(self):
        self.state = State.WAITING  # ゲームの状態
        self.message_dic = {}       # ゲーム進行毎のメッセージのIDを控える辞書
        self.playerList = []        # 参加プレイヤーのリスト
        self.odaiDeck = []          # お題の山札
        self.answerer = 0           # 回答者のID
        self.nowOdai = ''           # 現在のお題
        self.proposeList = []       # ヒントのメッセージのIDを控えるリスト
        self.checkedPlayerList = [] # チェックしたプレイヤーのIDを控えるリスト
        self.duplicateHintID = {}   # 被ったヒントのメッセージID
        self.duplicateHintText = {} # 被ったヒントのテキスト
        self.okng = 0               # 〇☓集計用
        self.Round = 1              # 巡目
        self.Hit = 0                # 正答数
        self.answerMessageID = 0    # 回答メッセージのID
        print('ゲームの進行状況を初期化')

    def __init__(self, client):
        self.discordClient = client
        self.Odai = odaiManager()
        self.initGame()
        print('justoneManagerを初期化')

    def isMessageSuitStatus(self, stat : State, m_id : int) -> bool:
        return stat == self.state and m_id == self.message_dic.get(stat)

    def playersName(self) -> str:
        text = ''
        for p_id in self.playerList:
            text += Mention(p_id)
        return text

    def proceedState(self, nextState):
        self.checkedPlayerList = []
        self.okng = 0
        self.state = nextState
        print(nextState)
    
    async def proceedRound(self, payload : RawReactionActionEvent, channel : TextChannel, text : str):
        if self.duplicateHintText:
            text += '重複/違反したヒント\n'
            for m_id in self.duplicateHintText.keys():
                text += Mention(m_id) + '：' + self.duplicateHintText[m_id] + '\n'
            self.duplicateHintText = {}
        self.Round += 1
        self.playerList.append(self.answerer)
        self.checkedPlayerList = []
        self.message_dic = {}
        self.okng = 0
        if self.odaiDeck:
            self.state = State.WAITPROPOSING
            self.nowOdai = self.odaiDeck.pop()
            self.answerer = self.playerList.pop(0)
            mem = self.discordClient.get_guild(payload.guild_id).get_member(self.answerer)
            text += str(self.Round) + '巡目 正答数:' + str(self.Hit) + ' 残り山札:' + str(len(self.odaiDeck)) + '\n回答者は**' + Mention(self.answerer) + '**です'
            message = await channel.send(text)
            print(text)
            await channel.set_permissions(mem, read_messages=False, send_messages = False)
            message = await channel.send('\nお題は||' + self.nowOdai + '||です\n出題者(' + self.playersName() + ')はヒントを出してください(' + EMOJI_CHECK + 'で完了)')
            self.message_dic[State.WAITPROPOSING] = message.id
            await message.add_reaction(EMOJI_CHECK)
            print('出題開始メッセージを確認')
            return
        else:
            text += 'ゲーム終了！今回の正答数は**' + str(self.Hit) + '**でした\n参加者：' + self.playersName()
            sendMessage = await channel.send(text)
            await sendMessage.pin()
            self.initGame()
            self.proceedState(State.ENTRY)
            sendMessage = await channel.send('次のゲームに参加する場合はこのメッセージにリアクションしてください(' + EMOJI_CHECK + 'で完了)')
            print('参加申請メッセージを送出')
            self.message_dic[State.ENTRY] = sendMessage.id
            await sendMessage.add_reaction('✋')
            await sendMessage.add_reaction(EMOJI_CHECK)
            return

    # メッセージ受信時の処理
    async def onMessage(self, receiveMessage : Message):
        # コマンド対応
        if receiveMessage.content == '/help':
            print('/helpを確認')
            text = Mention(receiveMessage.author.id) + '\n**JustOneの遊び方**：\nhttps://yaneurado.com/just-one/\ndiscordのチャットは**||**で内容を挟むことで黒塗りが出来ます\n||こんなかんじ||\n'
            text += '**botコマンド**：\n/odai　お題を一つ表示します\n/justone　JustOneを開始します\n/entry　進行中のゲームに参加します\n/quit　現在進行しているJustOneを中止します\n/justiceone　左から5列目　真ん中のマスに　正義のコブシ！'
            await receiveMessage.channel.send(text)

        if receiveMessage.content == '/odai' and self.state == State.WAITING:
            print('/odaiを確認')
            await receiveMessage.channel.send('お題は||' + self.Odai.GetOdai() + '||です')

        if receiveMessage.content == '/reload':
            print('/reloadを確認')
            self.Odai.readOdai()
            print('お題を再装填')

        if receiveMessage.content == '/justone' and self.state == State.WAITING:
            print('/justoneを確認')
            self.initGame()
            self.proceedState(State.ENTRY)
            sendMessage = await receiveMessage.channel.send('JustOneがはじまります\n参加するにはこのメッセージにリアクションしてください(' + EMOJI_CHECK + 'で完了)')
            print('参加申請メッセージを送出')
            self.message_dic[State.ENTRY] = sendMessage.id
            await sendMessage.add_reaction('✋')
            await sendMessage.add_reaction(EMOJI_CHECK)

        if receiveMessage.content == '/entry' and self.state != State.WAITING:
            print('/entryを確認')
            if receiveMessage.author.id in self.playerList or receiveMessage.author.id == self.answerer:
                return
            self.playerList.append(receiveMessage.author.id)
            await receiveMessage.channel.send(Mention(receiveMessage.author.id) + 'が参加しました')

        if receiveMessage.content == '/quit' and self.state != State.WAITING:
            print('/quitを確認')
            if not (receiveMessage.author.id in self.playerList or receiveMessage.author.id == self.answerer):
                return
            if self.answerer != 0:
                await receiveMessage.channel.set_permissions(receiveMessage.guild.get_member(self.answerer), read_messages=True, send_messages = True)
            await receiveMessage.channel.send('ゲームは中断されました')
            self.__init__

        if self.state == State.WAITPROPOSING and receiveMessage.author.id in self.playerList and '//' not in receiveMessage.content:
            print('ヒントを受信:' + receiveMessage.content)
            self.proposeList.append(receiveMessage.id)

        if self.state == State.WAITANSWER and receiveMessage.author.id == self.answerer:
            print('回答を確認')
            self.proceedState(State.CHECKANSWER)
            self.answerMessageID = receiveMessage.id
            waitAnsMessge = await receiveMessage.channel.fetch_message(self.message_dic[State.WAITANSWER])
            await waitAnsMessge.clear_reactions()
            sendMessage = await receiveMessage.channel.send('出題者(' + self.playersName() + ')は回答の正誤を判定してください')
            self.message_dic[State.CHECKANSWER] = sendMessage.id
            await sendMessage.add_reaction(EMOJI_OK)
            await sendMessage.add_reaction(EMOJI_NG)
            print('回答確認メッセージを確認')

    async def onAddReaction(self, payload : RawReactionActionEvent, channel : TextChannel):
        # 参加メッセージへのリアクション対応
        if self.isMessageSuitStatus(State.ENTRY, payload.message_id):
            print('参加申請メッセージへのリアクションを確認')
            if str(payload.emoji) == EMOJI_CHECK and payload.user_id in self.playerList:
                if len(self.playerList) < 2:
                    await channel.send('JustOneを中止しました')
                    self.initGame()
                    return
                self.proceedState(State.ENTRYCHECK)
                sendMessage = await channel.send(self.playersName() + '\n参加者は以上でよろしいですか？')
                print('ゲーム開始確認メッセージ送出')
                self.message_dic[State.ENTRYCHECK] = sendMessage.id
                await sendMessage.add_reaction(EMOJI_OK)
                await sendMessage.add_reaction(EMOJI_NG)
            else:
                if payload.user_id in self.playerList:
                    return
                self.playerList.append(payload.user_id)
                print(str(payload.user_id) + ' の参加を登録')

        # 開始確認メッセージ
        if self.isMessageSuitStatus(State.ENTRYCHECK, payload.message_id):
            if payload.user_id not in self.playerList or payload.user_id in self.checkedPlayerList or (str(payload.emoji) != EMOJI_NG and str(payload.emoji) != EMOJI_OK):
                return
            print('開始確認メッセージへのリアクションを確認')
            self.checkedPlayerList.append(payload.user_id)
            if str(payload.emoji) == EMOJI_NG:
                self.proceedState(State.ENTRY)
                await channel.get_partial_message(payload.message_id).delete()

            if len(self.playerList) > len(self.checkedPlayerList):
                return
                
            self.proceedState(State.WAITPROPOSING)
            random.shuffle(self.playerList)
            self.answerer = self.playerList.pop(0)
            for i in range(13):
                self.odaiDeck.append(self.Odai.GetOdai())
            self.nowOdai = self.odaiDeck.pop()
            mem = self.discordClient.get_guild(payload.guild_id).get_member(self.answerer)
            await channel.send('ゲームを開始します\n最初の回答者は**' + Mention(self.answerer) + '**です')
            await channel.set_permissions(mem, read_messages=False, send_messages = False)
            sendMessage = await channel.send('お題は||' + self.nowOdai + '||です\n出題者(' + self.playersName() + ')はヒントを出してください(' + EMOJI_CHECK + 'で完了)')
            self.message_dic[State.WAITPROPOSING] = sendMessage.id
            await sendMessage.add_reaction(EMOJI_CHECK)
            print('ヒント出題開始メッセージを確認')

        if self.isMessageSuitStatus(State.WAITPROPOSING, payload.message_id):
            print('ヒント出題開始メッセージへのリアクションを確認')
            if not payload.user_id in self.playerList:
                return
            if str(payload.emoji) == EMOJI_CHECK and payload.user_id not in self.checkedPlayerList:
                self.checkedPlayerList.append(payload.user_id)
                if len(self.checkedPlayerList) >= len(self.playerList):
                    print('全員がヒント出題したためヒント確認へ移行')
                    self.proceedState(State.CHECKPROPOSING)
                    for m_id in self.proposeList:
                        proposeMessage = await channel.fetch_message(m_id)
                        await proposeMessage.add_reaction(EMOJI_NG)
                    sendMessage = await channel.send(self.playersName() + '重複や違反がないか確認してください(' + EMOJI_NG + 'で削除、' + EMOJI_CHECK + 'で完了)')
                    self.message_dic[State.CHECKPROPOSING] = sendMessage.id
                    await sendMessage.add_reaction(EMOJI_CHECK)
                    print('ヒント出題確認メッセージを確認')

        if self.state == State.CHECKPROPOSING and payload.message_id in self.proposeList and payload.user_id in self.playerList:
            if str(payload.emoji) != EMOJI_NG:
                return
            print('ヒントへのリアクションを確認')
            proposeMessage = await channel.fetch_message(payload.message_id)
            self.duplicateHintID[proposeMessage.author.id] = payload.message_id
            await proposeMessage.add_reaction(EMOJI_DOKURO)
            print('重複/違反したヒントを登録')

        if self.isMessageSuitStatus(State.CHECKPROPOSING, payload.message_id):
            print('ヒント確認メッセージへのリアクションを確認')
            if not payload.user_id in self.playerList:
                return
            if str(payload.emoji) == EMOJI_CHECK and payload.user_id not in self.checkedPlayerList:
                self.checkedPlayerList.append(payload.user_id)
                if len(self.checkedPlayerList) >= len(self.playerList):
                    print('全員がヒント確認したため回答へ移行')
                    self.proceedState(State.WAITANSWER)
                    for m_id in self.duplicateHintID.values():
                        self.proposeList.remove(m_id)
                        deleteMessage = await channel.fetch_message(m_id)
                        self.duplicateHintText[deleteMessage.author.id] = deleteMessage.content
                        if not '||' in self.duplicateHintText[deleteMessage.author.id]:
                            self.duplicateHintText[deleteMessage.author.id] = '||' + self.duplicateHintText[deleteMessage.author.id] + '||'
                        await deleteMessage.delete()
                    self.duplicateHintID = {}
                    text = ''
                    for m_id in self.proposeList:
                        proposeMessage = await channel.fetch_message(m_id)
                        t:str = proposeMessage.content
                        await proposeMessage.clear_reactions()
                        print(t)
                        text += Mention(proposeMessage.author.id) + '：' + t.replace('||', '') + '\n'
                    self.proposeList = []
                    await channel.get_partial_message(payload.message_id).delete()
                    await channel.set_permissions(self.discordClient.get_guild(payload.guild_id).get_member(self.answerer), read_messages=True, send_messages = True)
                    sendMessage = await channel.send(text + 'ヒントが出揃いました！**' + Mention(self.answerer) + '**は回答してください(' + EMOJI_NG + 'でパス)')
                    self.message_dic[State.WAITANSWER] = sendMessage.id
                    await sendMessage.add_reaction(EMOJI_NG)
                    print('回答開始メッセージを送信')

        if self.state == State.WAITANSWER and payload.user_id == self.answerer:
            if str(payload.emoji) == EMOJI_NG:
                text = 'パスが選択されました\nお題は||' + self.nowOdai + '||でした\n'
                await self.proceedRound(payload, channel, text)

        if self.isMessageSuitStatus(State.CHECKANSWER, payload.message_id):
            print('回答確認メッセージへのリアクションを確認')
            if not payload.user_id in self.playerList:
                return
            if (str(payload.emoji) == EMOJI_OK or str(payload.emoji) == EMOJI_NG) and payload.user_id not in self.checkedPlayerList:
                self.checkedPlayerList.append(payload.user_id)
                if str(payload.emoji) == EMOJI_OK:
                    self.okng += 1
                else:
                    self.okng -= 1
                if len(self.checkedPlayerList) >= len(self.playerList):
                    print('全員が回答確認したため正誤判定')
                    sendMessage = await channel.fetch_message(payload.message_id)
                    text = ''
                    if self.okng > 0:
                        text += '**正解！**お題は||' + self.nowOdai + '||でした\n'
                        self.Hit += 1
                    else:
                        text += '**不正解…**お題は||' + self.nowOdai + '||でした\n'
                        if self.odaiDeck:
                            self.odaiDeck.pop()
                            text += '山札が1枚減ります\n'
                    ansMessage = await channel.fetch_message(self.answerMessageID)
                    text += Mention(self.answerer) + 'の回答:||' + self.Odai.alignLength(ansMessage.content) + '||\n'
                    await ansMessage.delete()
                    await self.proceedRound(payload, channel, text)

    async def onRemoveReaction(self, payload : RawReactionActionEvent, channel : TextChannel):
        # 参加メッセージへのリアクション対応
        if self.isMessageSuitStatus(State.ENTRY, payload.message_id):
            print('参加申請メッセージへのリアクション削除を確認')
            if str(payload.emoji) != EMOJI_CHECK and payload.user_id in self.playerList:
                self.playerList.remove(payload.user_id)
                print(str(payload.user_id) + ' の参加を取り消し')

        if self.isMessageSuitStatus(State.WAITPROPOSING, payload.message_id):
            print('ヒント出題メッセージへのリアクション削除を確認')
            if str(payload.emoji) != EMOJI_CHECK or payload.user_id not in self.checkedPlayerList:
                return
            self.checkedPlayerList.remove(payload.user_id)
            print('ヒント出題完了を取り消し')

        if self.state == State.CHECKPROPOSING and payload.message_id in self.proposeList and payload.user_id in self.playerList:
            if str(payload.emoji) != EMOJI_NG:
                return
            print('ヒントへのリアクション削除を確認')
            proposeMessage = await channel.fetch_message(payload.message_id)
            for reaction in proposeMessage.reactions:
                if str(reaction.emoji) != EMOJI_NG: continue
                if reaction.count <= 1: break
                else: return
            del(self.duplicateHintID[proposeMessage.author.id])
            await proposeMessage.clear_reaction(EMOJI_DOKURO)
            print('ヒント削除登録を取り消し')

        if self.isMessageSuitStatus(State.CHECKPROPOSING, payload.message_id):
            print('ヒント確認メッセージへのリアクション削除を確認')
            if str(payload.emoji) != EMOJI_CHECK or payload.user_id not in self.checkedPlayerList:
                return
            self.checkedPlayerList.remove(payload.user_id)
            print('ヒント確認を取り消し')
            
