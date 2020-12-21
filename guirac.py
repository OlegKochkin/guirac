#!/bin/python3

import os,sys,subprocess,traceback,time
from subprocess import Popen, PIPE
from PyQt5 import QtWidgets,uic,QtGui
from PyQt5.QtWidgets import QTreeWidgetItem,QMessageBox,QWidget,QMenu,QDialog,QTableWidgetItem,QHeaderView,QLabel
from PyQt5.QtCore import QSettings,Qt,QPoint,QTimer

cfg = QSettings('guirac','guirac')

DEBUG = False

COPIRIGHT = 'GUIRac v 1.0-3 (19.12.2020). Copyright © 2020 Oleg Kochkin. License GPL.'
# https://github.com/OlegKochkin/guirac,

RAS_PORT = cfg.value('RASPort','1545')
RAC = cfg.value('RACPath','/opt/1C/v8.3/x86_64/rac')
WORK_HOST = (os.uname()[1]).rstrip().upper()

if WORK_HOST == cfg.value('WorkHost',''):
	CMD_PREFIX = ''
else:
	CMD_PREFIX = cfg.value('CmdPrefix','')
	WORK_HOST = (subprocess.check_output(CMD_PREFIX + ' ' + 'hostname', shell=True).decode('utf-8')).rstrip()

DB_TYPES = ['PostgreSQL','MSSQLServer','IBMDB2','OracleDatabase']

ERR_BASE_RIGHTS = 'Недостаточно прав пользователя на информационную базу'
ERR_CONN_SERVER = 'Ошибка соединения с сервером'
ERR_CLUSTER_RIGHTS = 'Администратор кластера не аутентифицирован'
ERR_BASE_CREATE = 'Невозможно создать базу'
ERR_DB_USER = 'password authentication failed for user'

class fm(QtWidgets.QMainWindow):
	def __init__(self):
		QtWidgets.QMainWindow.__init__(self)
		uic.loadUi('ui/mainwindow.ui', self)
		self.setWindowTitle(COPIRIGHT)
		self.StatusBarStyle = self.statusBar().styleSheet()
		self.resize(cfg.value('Width',1000,type=int),cfg.value('Height',500,type=int))
		self.setGeometry(cfg.value('Left',50,type=int),
			cfg.value('Top',50,type=int),
			cfg.value('Width',1000,type=int),
			cfg.value('Height',500,type=int))

		self.savedLogins = cfg.value('Logins',{})
		self.sessionLogins = cfg.value('Logins',{})

		self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tree.customContextMenuRequested.connect(self.treeContextMenuRequested)
		self.tree.currentItemChanged.connect(self.sessionsCelChg)
		self.tree.clicked.connect(self.sessionsCelChg)
#		self.tree.clicked.connect(self.treeClicked)

		self.tRight.setContextMenuPolicy(Qt.CustomContextMenu)
		self.tRight.customContextMenuRequested.connect(self.tRightContextMenuRequested)
		self.tRight.clicked.connect(self.tRightClicked)

		self.hosts = cfg.value('Hosts',{WORK_HOST:RAS_PORT})
		
		cmd = CMD_PREFIX + ' ' + RAC + ' -v'
		if DEBUG: print('cmd:',cmd)
		ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
		ret = ret.decode('utf-8').rstrip()
		err = err.decode('utf-8')
		if len(err) > 0:
			if DEBUG: print('Есть ошибки:',err)
			msg = QMessageBox()
			msg.setIcon(QMessageBox.Critical)
			msg.setWindowTitle('Не обнаружена утилита RAC.')
			msg.setText('Не удалось запустить утилиту ' + CMD_PREFIX + ' ' + RAC)
			msg.setInformativeText('Проверьте работоспособность утилиты и путь к ней.')
			msg.setDetailedText('Путь к утилите по умолчанию: /opt/1C/v8.3/x86_64/rac\nИзменить его можно в переменной RACPath в файле ~/.config/guirac/guirac.conf\nВ случае самостоятельного указания пути к RAC, полный путь к утилите формируется из переменных в файле ~/.config/guirac/guirac.conf таким образом: CmdPrefix+\'  \'+RACPath')
			msg.exec()
			exit (1)
		else:
			if DEBUG: print('Есть возможность запуска RAC версии',ret)
			QTimer.singleShot(1,self.TreeUpdate)

	def TreeUpdate(self):
		app.processEvents()
		self.tree.clear()
		self.tRight.clear()
		self.tRight.setRowCount(0)
		self.tRight.setColumnCount(0)

		self.server_cap = QTreeWidgetItem(self.tree)
		self.server_cap.setText(0,'Серверы 1С Предприятия')
		self.server_cap.setExpanded(True)

		expanded = True
		sorted_hosts = list(self.hosts.keys())
		sorted_hosts.sort()
		self.Bases = {}
		for sel in sorted_hosts:
			sel_host = sel
			sel_port = self.hosts[sel]
			app.processEvents()
			self.Clusters = []
			host_work = self.getClusters(sel_host,sel_port)

			self.host_cap = QTreeWidgetItem()
			if not host_work:
				self.host_cap.setBackground(0, QtGui.QColor(255,128,128))
			self.host_cap.setText(0,sel_host)
			self.server_cap.addChild(self.host_cap)
			self.host_cap.setExpanded(False)

			for cluster in self.Clusters:
				self.Bases[cluster['cluster']] = []
				app.processEvents()
				self.clusters_cap = QTreeWidgetItem()
				self.clusters_cap.setText(0,'Кластеры')
				self.host_cap.addChild(self.clusters_cap)
				self.clusters_cap.setExpanded(expanded)
					
				self.cluster = QTreeWidgetItem()
				self.cluster.setText(0,cluster['name'])
				self.cluster.setText(1,sel_host)
				self.cluster.setText(2,cluster['cluster'])
				self.clusters_cap.addChild(self.cluster)
				self.cluster.setExpanded(expanded)

				if self.getBases(sel_host,sel_port,cluster['cluster']):
					self.bases_cap = QTreeWidgetItem()
					self.bases_cap.setText(0,'Информационные базы')
					self.bases_cap.setText(1,sel_host)
					self.bases_cap.setText(2,sel_port)
					self.bases_cap.setText(3,cluster['cluster'])
					self.cluster.addChild(self.bases_cap)
					self.bases_cap.setExpanded(expanded)

					for base in self.Bases[cluster['cluster']]:
						app.processEvents()
						item = QTreeWidgetItem()
						item.setText(0,base['name'])
						item.setText(1,base['infobase'])
						item.setText(2,sel_host)
						item.setText(3,sel_port)
						item.setText(4,cluster['cluster'])
						self.bases_cap.addChild(item)

					self.sessions_cap = QTreeWidgetItem()
					self.sessions_cap.setText(0,'Сеансы')
					self.sessions_cap.setText(1,sel_host)
					self.sessions_cap.setText(2,sel_port)
					self.sessions_cap.setText(3,cluster['cluster'])
					self.cluster.addChild(self.sessions_cap)

					admins = self.getClasterAdmins(cluster['cluster'],sel_host,sel_port)
					if admins != None:
						if len(admins) > 0:
							self.admins_cap = QTreeWidgetItem()
							self.admins_cap.setText(0,'Администраторы')
							self.admins_cap.setText(1,sel_host)
							self.admins_cap.setText(2,sel_port)
							self.admins_cap.setText(3,cluster['cluster'])
							self.cluster.addChild(self.admins_cap)
							self.admins_cap.setExpanded(False)

							for admin in admins:
								item = QTreeWidgetItem()
								item.setText(0,admin['name'])
								item.setText(1,admin['auth'])
								item.setText(2,sel_host)
								item.setText(3,sel_port)
								item.setText(4,cluster['cluster'])
								item.setText(5,admin['os-user'])
								item.setText(6,admin['descr'])
								self.admins_cap.addChild(item)
#				expanded = False

	def getClasterAdmins(self,cluster,host,port):
		admins = []
		auth_cluster = self.getSessionAuth(cluster,'cluster')
		cmd = CMD_PREFIX + ' ' + RAC + ' cluster admin list --cluster=' + cluster + ' ' + auth_cluster + host + ':' + port
		if DEBUG: print (cmd)
		ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
		ret = ret.decode('utf-8')
		err = err.decode('utf-8')
		if len(err) > 0:
			if DEBUG: print('Есть ошибки:',err)
			self.Mess('warn',err + ' на '+host+':'+port)
		else:
			if DEBUG: print (ret)

			ar = ret.split('\n')
			admin = {}
			i = 0
			for line in ar:
				if line.find(' : ') > 0:
					key = (line.split(' : '))[0].strip()
					value = (line.split(' : '))[1].strip()
					admin[key] = value
					if key == 'descr':
						admins.append(admin)
						admin = {}
						i = i+1
			return admins
		

	def sessionsCelChg(self):
		try:
			if self.tree.currentItem().text(0) == 'Сеансы': self.getSessions()
			else:
				self.tRight.clear()
				self.tRight.setRowCount(0)
				self.tRight.setColumnCount(0)
		except Exception: pass

	def defaultLogins(self):
		self.dDefaultLogins = QtWidgets.QDialog()
		uic.loadUi('ui/default_logins.ui',self.dDefaultLogins)
		def_logins = cfg.value('DefaultLogins',{})
		try:
			self.dDefaultLogins.eUser1C.setText(def_logins['user1c'])
			self.dDefaultLogins.ePasswd1C.setText(def_logins['passwd1c'])
			self.dDefaultLogins.eUserSQL.setText(def_logins['userSQL'])
			self.dDefaultLogins.ePasswdSQL.setText(def_logins['passwdSQL'])
		except Exception:
			pass
		if self.dDefaultLogins.exec():
			def_logins = {}
			def_logins['user1c'] = self.dDefaultLogins.eUser1C.text()
			def_logins['passwd1c'] = self.dDefaultLogins.ePasswd1C.text()
			def_logins['userSQL'] = self.dDefaultLogins.eUserSQL.text()
			def_logins['passwdSQL'] = self.dDefaultLogins.ePasswdSQL.text()
			cfg.setValue('DefaultLogins',def_logins)
			cfg.sync()

	def getSessionAuth(self,id,type):
		ret = ' '
		if id in self.sessionLogins:
			if 'login' in self.sessionLogins[id]:
				if len(ret[0]) > 0:
					ret = ' --' + type + '-user=' + self.sessionLogins[id]['login'] + ' --' + type +'-pwd=' + self.sessionLogins[id]['passwd'] + ' '
		return ret

	def getSessions(self):
		self.tRight.clear()
		self.tRight.setRowCount(0)
		self.tRight.setColumnCount(0)
		self.Mess('info','Получение информации о сеансах...')
		app.processEvents()
		host = self.tree.currentItem().text(1)
		port = self.tree.currentItem().text(2)
		cluster = self.tree.currentItem().text(3)
		auth_cluster = self.getSessionAuth(cluster,'cluster')
		cmd = CMD_PREFIX + ' ' + RAC + ' session list --cluster=' + cluster + ' ' + auth_cluster + host + ':' + port
		if DEBUG: print (cmd)
		ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
		ret = ret.decode('utf-8')
		err = err.decode('utf-8')
		if len(err) > 0:
			if DEBUG: print('Есть ошибки:',err)
			self.Mess('warn',err + ' '+name+' на '+host+':'+port)
		else:
			if DEBUG: print (ret)
			ar = ret.split('\n')
			self.Sessions = []
			session = {}
			i = 0
			start_session = False
			for line in ar:
				if line.find(' : ') > 0:
					start_session = True
					key = (line.split(' : '))[0].strip()
					value = (line.split(' : '))[1].strip()
					session[key] = value
					if key == 'infobase':
						for b in self.Bases[cluster]:
							if b['infobase'] == value:
								session['base-name'] = b['name']
					if key == 'host':
						session['ras-port'] = port
				if line == '' and start_session:
					self.Sessions.append(session)
					session = {}
					i = i+1
					start_session = False
			if len(self.Sessions) > 0:
				labels = []
				for l in self.Sessions[0]:
					labels.append(l)
				self.tRight.setColumnCount(len(labels))
				self.tRight.setHorizontalHeaderLabels(labels)
				for i,s in enumerate(self.Sessions[0]):
					self.tRight.hideColumn(i)
					if s == 'base-name':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('База')
					if s == 'user-name':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('Пользователь')
					if s == 'host':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('Узел')
					if s == 'app-id':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('Приложение')
					if s == 'started-at':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('Начало сеанса')
					if s == 'last-active-at':
						self.tRight.showColumn(i)
						self.tRight.horizontalHeaderItem(i).setText('Последняя активность')
				for s in self.Sessions:
					row = self.tRight.rowCount()
					self.tRight.setRowCount(row + 1)
					for i,a in enumerate(s):
						if s[a] == '1CV8': s[a] = 'Толстый клиент'
						if s[a] == '1CV8C': s[a] = 'Тонкий клиент'
						if s[a] == 'BackgroundJob': s[a] = 'Фоновое задание'
						self.tRight.setItem(row, i, QTableWidgetItem(s[a]))
					self.tRight.horizontalHeader().resizeSections(QHeaderView.ResizeToContents)
			self.MessOff()

	def tRightContextMenuRequested(self,point):
		mpoint = QPoint()
		mpoint.setX(point.x() + self.tRight.x())
		mpoint.setY(point.y() + self.menubar.height() + self.tRight.y())
		if not self.tRight.indexAt(point).isValid(): return
		menu = QMenu(self)
		menu.addAction('Завершить выбранные сеансы',self.closeSessions)
		action = menu.exec_(self.mapToGlobal(mpoint))
		
	def closeSessions(self):
		self.Mess('info','Завершение сеансов...')
		app.processEvents()
		indexes = self.tRight.selectionModel().selection().indexes()
		prev_row = -1
		sel_ses = []
		host = self.tree.currentItem().text(1)
		port = self.tree.currentItem().text(2)
		cluster = self.tree.currentItem().text(3)
		auth_cluster = self.getSessionAuth(cluster,'cluster')
		for i in indexes:
			if i.row() != prev_row:
				sel_ses.append(self.tRight.item(i.row(),0).text())
				prev_row = i.row()

		for session in sel_ses:
			cmd = CMD_PREFIX + ' ' + RAC + ' session terminate --cluster=' + cluster + ' --session=' + session + ' ' + auth_cluster + host + ':' + port
			if DEBUG: print(cmd)
			try: ret = (subprocess.check_output(cmd, shell=True)).decode('utf-8')
			except Exception:
				if DEBUG: print(traceback.format_exc())
				if DEBUG: print("DEBUG: Невозможно завершить сеанс.")
			else:
				if DEBUG: print(ret)
				self.MessOff()
				self.getSessions()

	def tRightClicked(self,point):
		pass

	def ServerCreate(self):
		self.dNewServer = QtWidgets.QDialog()
		uic.loadUi('ui/server_create.ui',self.dNewServer)
		if self.dNewServer.exec():
			if not self.dNewServer.eHost.text() in self.hosts:
				self.hosts[self.dNewServer.eHost.text().upper()] = self.dNewServer.ePort.text()
				self.TreeUpdate()
				cfg.setValue('Hosts',self.hosts)
				cfg.sync()

	def serverDelete(self):
		self.hosts.pop(self.tree.currentItem().text(0))
		cfg.setValue('Hosts',self.hosts)
		cfg.sync()
		self.TreeUpdate()

	def treeContextMenuRequested(self,point):
		mpoint = QPoint()
		mpoint.setX(point.x() + 10 + self.tree.x())
		mpoint.setY(point.y() + self.menubar.height())
		try:
			if self.tree.currentItem().text(0) == 'Серверы 1С Предприятия':
				menu = QMenu(self)
				menu.addAction('Создать подключение к службе RAS...',self.ServerCreate)
				action = menu.exec_(self.mapToGlobal(mpoint))
		except Exception: return
		try: parent = self.tree.currentItem().parent()
		except Exception: return
		if parent == None: return
		if not self.tree.indexAt(point).isValid(): return
		parent = self.tree.currentItem().parent()
		
		if parent.text(0) == 'Серверы 1С Предприятия':
			menu = QMenu(self)
			menu.addAction('Удалить подключение к службе RAS',self.serverDelete)
			action = menu.exec_(self.mapToGlobal(mpoint))
			
		try:
			if parent.text(0) == 'Информационные базы':
				menu = QMenu(self)
				menu.addAction('Свойства базы...',self.BaseProp)
				menu.addAction('Удалить базу...',self.BaseDelete)
				action = menu.exec_(self.mapToGlobal(mpoint))
		except Exception: pass

		try:
			if self.tree.currentItem().text(0) == 'Информационные базы':
				menu = QMenu(self)
				menu.addAction('Создать базу...',self.BaseCreate)
				action = menu.exec_(self.mapToGlobal(mpoint))
		except Exception: return

	def BaseDelete(self):
		self.dlgBaseDelete = QtWidgets.QDialog()
		uic.loadUi('ui/base_delete.ui',self.dlgBaseDelete)
		name = self.tree.currentItem().text(0)
		host = self.tree.currentItem().text(2)
		port = self.tree.currentItem().text(3)
		self.dlgBaseDelete.setWindowTitle('Удаление базы '+name+' на '+host+':'+port)
		if self.dlgBaseDelete.exec():
			self.Mess('info','Удаление базы '+name+' на '+host+':'+port+'...')
			app.processEvents()
			infobase = self.tree.currentItem().text(1)
			cluster = self.tree.currentItem().text(4)
			drop_database = ''
			clear_database = ''
			if self.dlgBaseDelete.gpDelete.isChecked():
				if self.dlgBaseDelete.cbDelete.isChecked():
					drop_database = ' --drop-database'
				if self.dlgBaseDelete.cbClear.isChecked():
					drop_database = ' --clear-database'
			repeat = True
			while(repeat):
				auth_cluster = self.getSessionAuth(cluster,'cluster')
				auth_base = self.getSessionAuth(infobase,'infobase')
				cmd = CMD_PREFIX + ' ' + RAC + ' infobase --cluster='+cluster + ' drop --infobase=' + infobase + drop_database + clear_database + auth_cluster + auth_base + ' ' + host + ':' + port
				if DEBUG: print (cmd)
				ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
				ret = ret.decode('utf-8')
				err = err.decode('utf-8')
				if len(err) > 0:
					if DEBUG: print('Есть ошибки:',err)
					if ERR_BASE_RIGHTS in err:
						self.Mess('warn',ERR_BASE_RIGHTS + ' '+name+' на '+host+':'+port)
						if not self.BaseLogPass(name,host,port): repeat = False
				else:
					repeat = False
					if DEBUG: print('ret:',ret)

					if infobase in self.savedLogins:
						self.savedLogins.pop(infobase)
						cfg.setValue('Logins',self.savedLogins)
						cfg.sync()

					self.MessOff()
					self.TreeUpdate()

	def BaseCreate(self):
		self.dlgBaseCreate = QtWidgets.QDialog()
		uic.loadUi('ui/base_create.ui',self.dlgBaseCreate)
		def_logins = cfg.value('DefaultLogins',{})
		try:
			self.dlgBaseCreate.eDBUser.setText(def_logins['userSQL'])
			self.dlgBaseCreate.eDBPasswd.setText(def_logins['passwdSQL'])
		except Exception:
			pass
		for dpt in DB_TYPES: self.dlgBaseCreate.cbDBms.addItem(dpt)
		host = self.tree.currentItem().text(1)
		port = self.tree.currentItem().text(2)
		self.dlgBaseCreate.setWindowTitle('Создание базы на '+host+':'+port)
		if self.dlgBaseCreate.exec():
			name = self.dlgBaseCreate.eName.text()
			self.Mess('info','Создание базы '+name+' на '+host+':'+port+'...')
			app.processEvents()
			host = self.tree.currentItem().text(1)
			port = self.tree.currentItem().text(2)
			cluster = self.tree.currentItem().text(3)
			dbms = self.dlgBaseCreate.cbDBms.currentText()
			dbserver = self.dlgBaseCreate.eDBServer.text()
			dbname = self.dlgBaseCreate.eDBName.text()
			dbuser = self.dlgBaseCreate.eDBUser.text()
			dbpwd = self.dlgBaseCreate.eDBPasswd.text()
			descr = self.dlgBaseCreate.eDescr.text()
			lic = 'deny'
			if self.dlgBaseCreate.cbLic.isChecked(): lic = 'allow'
			createdatabase = ''
			if self.dlgBaseCreate.cbDBCreate.isChecked(): createdatabase = '--create-database '

			auth_cluster = self.getSessionAuth(cluster,'cluster')
			self.Mess('info','Создание базы '+name+' на '+host+':'+port)
			app.processEvents()
			cmd = CMD_PREFIX + ' ' + RAC + ' infobase --cluster=' + cluster + ' create ' + createdatabase + '--name='+name + ' --dbms=' + dbms+' --db-server=' + dbserver + ' --db-name=' + dbname + ' --locale=ru --db-user=' + dbuser+' --db-pwd=' + dbpwd + ' --license-distribution=' + lic + ' --descr=' + descr + ' ' + auth_cluster + host + ':' + port
			if DEBUG: print (cmd)
			ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
			ret = ret.decode('utf-8')
			err = err.decode('utf-8')
			if len(err) > 0:
				if DEBUG: print('Есть ошибки:',err)
				if ERR_BASE_CREATE in err:
					self.Mess('warn',ERR_BASE_CREATE + ' ' + host + ':' + port)
				if ERR_CLUSTER_RIGHTS in err:
					self.Mess('warn',ERR_CLUSTER_RIGHTS + ' ' + host + ':' + port)
				if ERR_DB_USER in err:
					self.Mess('warn','Ошибка аутентификации на сервере баз данных' + ' ' + host + ':' + port)
			else:
				if DEBUG: print (ret)
				self.MessOff()
				self.TreeUpdate()

	def BaseProp(self):
		self.dlgBaseProp = QtWidgets.QDialog()
		uic.loadUi('ui/base_prop.ui',self.dlgBaseProp)
		name = self.tree.currentItem().text(0)
		infobase = self.tree.currentItem().text(1)
		host = self.tree.currentItem().text(2)
		port = self.tree.currentItem().text(3)
		cluster = self.tree.currentItem().text(4)
		repeat = True
		while(repeat):
			auth_cluster = self.getSessionAuth(cluster,'cluster')
			auth_base = self.getSessionAuth(infobase,'infobase')
			self.Mess('info','Получение свойств базы '+name+' на '+host+':'+port)
			app.processEvents()
			cmd = CMD_PREFIX + ' ' + RAC + ' infobase info --cluster=' + cluster + ' --infobase=' + infobase + auth_cluster + auth_base + host + ':' + port
			if DEBUG: print (cmd)
			ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
			ret = ret.decode('utf-8')
			err = err.decode('utf-8')
			if len(err) > 0:
				if DEBUG: print('Есть ошибки:',err)
				if ERR_CLUSTER_RIGHTS in err:
					self.Mess('warn',ERR_CLUSTER_RIGHTS + ' ' + host + ':' + port)
					if not self.clusterLogPass(cluster,host,port): repeat = False
				if ERR_BASE_RIGHTS in err:
					self.Mess('warn',ERR_BASE_RIGHTS + ' '+name+' на '+host+':'+port)
					if not self.BaseLogPass(name,host,port): repeat = False
			else:
				repeat = False
				if DEBUG: print('ret:',ret)

				ar = ret.split('\n')
				BaseInfo = {}
				for line in ar:
					if line.find(' : ') > -1:
						key = (line.split(' : '))[0].strip()
						value = (line.split(' : '))[1].strip()
						BaseInfo[key]=value
				self.MessOff()
				self.dlgBaseProp.eName.setText(BaseInfo['name'])
				self.dlgBaseProp.eDescr.setText(BaseInfo['descr'].replace('"','').replace('\ ',' '))
				self.dlgBaseProp.eDBServer.setText(BaseInfo['db-server'])
				for dpt in DB_TYPES: self.dlgBaseProp.cbDBType.addItem(dpt)
				self.dlgBaseProp.cbDBType.setCurrentText(BaseInfo['dbms'])
				self.dlgBaseProp.eDBName.setText(BaseInfo['db-name'])
				self.dlgBaseProp.eDBUser.setText(BaseInfo['db-user'])
				if BaseInfo['license-distribution'] == 'allow': self.dlgBaseProp.cbLic.setCheckState(2)
				else: self.dlgBaseProp.cbLic.setCheckState(0)
				if BaseInfo['sessions-deny'] == 'on': self.dlgBaseProp.gpBlock.setChecked(1)
				else: self.dlgBaseProp.gpBlock.setChecked(0)
				self.dlgBaseProp.eBlockStart.setText(BaseInfo['denied-from'].replace('T',' '))
				self.dlgBaseProp.eBlockEnd.setText(BaseInfo['denied-to'].replace('T',' '))
				self.dlgBaseProp.eBlockMess.setText(BaseInfo['denied-message'].replace('"','').replace('\ ',' '))
				self.dlgBaseProp.eBlockCode.setText(BaseInfo['permission-code'].replace('"',''))
				if BaseInfo['scheduled-jobs-deny'] == 'on': self.dlgBaseProp.cbRegl.setCheckState(2)
				else: self.dlgBaseProp.cbRegl.setCheckState(0)

				self.dlgBaseProp.setWindowTitle('Свойства базы '+name+' на '+host+':'+port)
				if self.dlgBaseProp.exec():
					self.Mess('info','Запись свойств базы '+name+' на '+host+':'+port)
					app.processEvents()
					Descr =    " --descr='" + self.dlgBaseProp.eDescr.text().replace(' ','\ ') + "'"
					DBServer = " --db-server=" + self.dlgBaseProp.eDBServer.text()
					DBType =   " --dbms=" + self.dlgBaseProp.cbDBType.currentText()
					DBName =   " --db-name='" + self.dlgBaseProp.eDBName.text() + "'"
					DBUser =   " --db-user='" + self.dlgBaseProp.eDBUser.text() + "'"
					DBPasswd = " --db-pwd='" +  self.dlgBaseProp.eDBPasswd.text() + "'"
					Lic =      " --license-distribution=deny"
					if self.dlgBaseProp.cbLic.isChecked(): Lic = " --license-distribution=allow"
					Block =    " --sessions-deny=off"
					if self.dlgBaseProp.gpBlock.isChecked(): Block = " --sessions-deny=on"
					BlockStart = " --denied-from='" + self.dlgBaseProp.eBlockStart.text().replace(' ','T') + "'"
					BlockEnd =   " --denied-to='" + self.dlgBaseProp.eBlockEnd.text().replace(' ','T') + "'"
					BlockMess =  " --denied-message='" + self.dlgBaseProp.eBlockMess.text().replace(' ','\ ') + "'"
					BlockCode =  " --permission-code='" + self.dlgBaseProp.eBlockCode.text().replace(' ','\ ') + "'"
					Regl = " --scheduled-jobs-deny=off"
					if self.dlgBaseProp.cbRegl.isChecked(): Regl = " --scheduled-jobs-deny=on"

					cmd = CMD_PREFIX + ' ' + RAC + ' infobase update --cluster=' + cluster +' --infobase=' + infobase + auth_cluster + auth_base + Descr + DBServer + DBType + DBName + DBUser + DBPasswd + Lic + Block + BlockStart + BlockEnd + BlockMess + BlockCode + Regl + ' ' + host + ':' + port
					if DEBUG: print (cmd)
					try: ret = (subprocess.check_output(cmd, shell=True)).decode('utf-8')
					except Exception:
						if DEBUG: print(traceback.format_exc())
						if DEBUG: print("DEBUG: Невозможно записать свойства базы "+name)
						self.Mess('warn','Не записаны свойства базы '+name+' на '+host+':'+port)
					else:
						if DEBUG: print (ret)
		self.MessOff()

	def Mess(self,type,message):
		self.statusBar().showMessage(message)
		if type =='info': self.statusBar().setStyleSheet("QStatusBar{background:#c7e1c4;}")
		if type =='warn': self.statusBar().setStyleSheet("QStatusBar{background:#ffa0a0;}")

	def MessOff(self):
		self.statusBar().showMessage('')
		self.statusBar().setStyleSheet(self.StatusBarStyle)

	def getClusters(self,host,port):
		self.Mess('info','Получение информации о кластерах с сервера '+host+':'+port+'...')
		app.processEvents()
		return_flag = True
		cmd = CMD_PREFIX + ' ' + RAC + ' cluster list ' + host + ':' + port
		if DEBUG: print(cmd)
		ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
		ret = ret.decode('utf-8')
		err = err.decode('utf-8')
		if len(err) > 0:
			if DEBUG: print('Есть ошибки:',err)
			if ERR_CONN_SERVER in err:
				self.Mess('warn',ERR_CONN_SERVER + ' ' + host + ':' + port)
				msg = QMessageBox()
				msg.setIcon(QMessageBox.Critical)
				msg.setWindowTitle(ERR_CONN_SERVER)
				msg.setText('Не удалось подключиться к службе RAS, расположенной на ' + host + ':' + port + '.')
				msg.setInformativeText('Запустите службу, если она остановлена.')
				msg.setDetailedText('Команда запуска службы:\nras --daemon cluster')
				msg.exec()
				return_flag = False
		else:	
			if DEBUG: print(ret)
			ar = ret.split('\n')
			lastkey = 'name'
			hash = {'cluster':'','host':'','port':'',lastkey:''}
			for line in ar:
				for key in hash:
					if line.find(key) == 0:
						hash[key] = (line.split(' : '))[1].strip()
						if key == lastkey:
							self.Clusters.append(hash)
							hash = {'cluster':'','host':'','port':'',lastkey:''}
			self.MessOff()
		return return_flag

	def clusterLogPass(self,cluster,host,port):
		self.dlgLogPass = QtWidgets.QDialog()
		uic.loadUi('ui/log_pass.ui',self.dlgLogPass)
		self.dlgLogPass.gbUser.setTitle('Имя администратора кластера')
		self.dlgLogPass.gbPasswd.setTitle('Пароль администратора кластера')
		self.dlgLogPass.cbSave.setText('Сохранить логин и пароль для этого кластера в в файле конфигурации')
		self.dlgLogPass.setWindowTitle('Аутентификация кластера на '+host+':'+port)
		def_logins = cfg.value('DefaultLogins',{})
		if 'user1c' in def_logins and 'passwd1c' in def_logins:
			self.dlgLogPass.eLogin.setText(def_logins['user1c'])
			self.dlgLogPass.ePasswd.setText(def_logins['passwd1c'])
		if cluster in self.sessionLogins and 'login' in self.sessionLogins[cluster] and 'passwd' in self.sessionLogins[cluster]:
			self.dlgLogPass.eLogin.setText(self.sessionLogins[cluster]['login'])
			self.dlgLogPass.ePasswd.setText(self.sessionLogins[cluster]['passwd'])
		ret = self.dlgLogPass.exec()
		if ret:
			self.sessionLogins[cluster] = {'login':self.dlgLogPass.eLogin.text(),'passwd':self.dlgLogPass.ePasswd.text()}
			if self.dlgLogPass.cbSave.isChecked():
				self.savedLogins[cluster] = {'login':self.dlgLogPass.eLogin.text(),'passwd':self.dlgLogPass.ePasswd.text()}
				cfg.setValue('Logins',self.savedLogins)
				cfg.sync()
		return ret
		
	def BaseLogPass(self,name,host,port):
		self.dlgLogPass = QtWidgets.QDialog()
		uic.loadUi('ui/log_pass.ui',self.dlgLogPass)
		self.dlgLogPass.gbUser.setTitle('Имя администратора базы')
		self.dlgLogPass.gbPasswd.setTitle('Пароль администратора базы')
		self.dlgLogPass.cbSave.setText('Сохранить логин и пароль для этой базы в в файле конфигурации')
		self.dlgLogPass.setWindowTitle('Аутентификация базы '+name+' на '+host+':'+port)
		infobase = self.tree.currentItem().text(1)
		def_logins = cfg.value('DefaultLogins',{})
		if 'user1c' in def_logins and 'passwd1c' in def_logins:
			self.dlgLogPass.eLogin.setText(def_logins['user1c'])
			self.dlgLogPass.ePasswd.setText(def_logins['passwd1c'])
		if infobase in self.sessionLogins and 'login' in self.sessionLogins[cluster] and 'passwd' in self.sessionLogins[cluster]:
			self.dlgLogPass.eLogin.setText(self.sessionLogins[infobase]['login'])
			self.dlgLogPass.ePasswd.setText(self.sessionLogins[infobase]['passwd'])
		ret = self.dlgLogPass.exec()
		if ret:
			self.sessionLogins[infobase] = {'login':self.dlgLogPass.eLogin.text(),'passwd':self.dlgLogPass.ePasswd.text()}
			if self.dlgLogPass.cbSave.isChecked():
				self.savedLogins[infobase] = {'login':self.dlgLogPass.eLogin.text(),'passwd':self.dlgLogPass.ePasswd.text()}
				cfg.setValue('Logins',self.savedLogins)
				cfg.sync()
		return ret

	def getBases(self,host,port,cluster):
		self.Mess('info','Получение информации о базах с сервера '+host+':'+port+'...')
		app.processEvents()
		repeat = True
		while(repeat):
			auth_cluster = self.getSessionAuth(cluster,'cluster')
			self.Mess('info','Получение списка баз на '+host+':'+port)
			app.processEvents()
			cmd = CMD_PREFIX + ' ' + RAC + ' infobase --cluster=' + cluster + ' summary list ' + auth_cluster + host + ':' + port
			if DEBUG: print('cmd:',cmd)
			ret,err = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).communicate()
			ret = ret.decode('utf-8')
			err = err.decode('utf-8')
			if len(err) > 0:
				return_flag = False
				if DEBUG: print('Есть ошибки:',err)
				if ERR_CLUSTER_RIGHTS in err:
					self.Mess('warn',ERR_CLUSTER_RIGHTS + ' ' + host + ':' + port)
					if not self.clusterLogPass(cluster,host,port): repeat = False
			else:
				repeat = False
				return_flag = True
		if DEBUG: print('ret:',ret)
		if DEBUG: print(ret)
		ar = ret.split('\n')
		lastkey = 'descr'
		hash = {'infobase':'','name':'',lastkey:''}
		for line in ar:
			for key in hash:
				if line.find(key) == 0:
					hash[key] = (line.split(' : '))[1].strip()
					if key == lastkey:
						self.Bases[cluster].append(hash)
						hash = {'infobase':'','name':'',lastkey:''}
		self.MessOff()
		return return_flag

	def closeEvent(self, event):
		cfg.setValue('Hosts',self.hosts)
#		cfg.setValue('Logins',self.savedLogins)
		cfg.setValue('Left',self.x())
		cfg.setValue('Top',self.y())
		cfg.setValue('Width',self.width())
		cfg.setValue('Height',self.height())
		cfg.sync()

app = QtWidgets.QApplication(sys.argv)
my_fm = fm()
my_fm.show()
sys.exit(app.exec_())
