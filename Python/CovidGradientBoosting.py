# -*- coding: utf-8 -*-
"""
Created on Mon Apr 20 16:48:01 2020

@author: andre-goncalves
"""

import pandas as pd
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score

#Faz a leitura da base
df = pd.read_csv("Dados/novo_covid_ajustado.csv")

#Definindo x, y
features = df.columns.difference(['RESULTADO'])
x = df[features]
y = df['RESULTADO']

#Normalização da base
normalizador = MinMaxScaler(feature_range=(0, 1))
normalizador.fit(x)
x.values[:] = normalizador.transform(x)

#Separa base treinamento e teste
xTreino, xTeste, yTreino, yTeste = train_test_split(x, y, stratify=y, train_size=0.7, random_state=1986)

#Balanceamento
treino = xTreino.join(yTreino)
qtdeDescartados = treino['RESULTADO'].value_counts()[0]
qtdeConfirmados = treino['RESULTADO'].value_counts()[1]
dfDescartados = treino[treino['RESULTADO'] == 0] #Separa a base de descartados
dfConfirmados = treino[treino['RESULTADO'] == 1] #Separa a base de confirmados

#Under sampling
#print('\nUnder Sampling')
#dfDescartadosUnder = dfDescartados.sample(qtdeConfirmados)
#dfUnder = pd.concat([dfDescartadosUnder, dfConfirmados], axis=0)
#xTreino = dfUnder[features].values
#yTreino = dfUnder['RESULTADO'].values

#Over sampling
#print('\nOver Sampling')
#dfConfirmadosOver = dfConfirmados.sample(qtdeDescartados, replace=True)
#dfOver = pd.concat([dfDescartados, dfConfirmadosOver], axis=0)
#xTreino = dfOver[features].values
#yTreino = dfOver['RESULTADO'].values

#Smote sampling
print('\nSmote Sampling')
oversample = SMOTE()
xTreino, yTreino = oversample.fit_resample(treino[features], treino['RESULTADO'])
xTreino = xTreino.values
yTreino = yTreino.values

#Define o classificador
classifier = GradientBoostingClassifier(random_state=1986)

#Treina com todos registros
classifier.fit(xTreino, yTreino) 

#Define o scoring
scoring = ['accuracy', 'balanced_accuracy', 'average_precision', 'recall', 'jaccard']
score = 'balanced_accuracy'

#Permutation Importance
print('\nPermutation Importance')
pi = permutation_importance(classifier, x, y, scoring=score, n_jobs=3, random_state=1986)

#Restringe as features
indFeatures = np.where((pi.importances_mean * 1000) >= 0.001)[0]
for i in pi.importances_mean[indFeatures].argsort()[::-1]:
    print('%s: %.2f' % (features[indFeatures[i]], pi.importances_mean[indFeatures[i]] * 1000))

xTreino = xTreino[:, indFeatures]
xTeste = xTeste[xTeste.columns[indFeatures]]
print('Qtde features selecionadas: ', len(xTeste.columns))

#K-fold
print('\n========== TUNING PARAMETERS ==========')
arrayYReal = []
arrayYPrediction = []
arrayAcuracia = []
arrayConfusion = np.array([[0, 0], [0, 0]])

kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=1986)

#Grid Search
paramGrid = {
        'loss': ['deviance', 'exponential'],
        'learning_rate': [0.1, 0.5],
        'n_estimators': [5, 25],
        'subsample': [1, 5],
        'criterion': ['friedman_mse', 'mse', 'mae']
        }

#Faz o processamento de treinamento com Tuning e Feature Selection
gridSearch = GridSearchCV(estimator=classifier, param_grid=paramGrid, scoring=scoring, refit=score, n_jobs=3)
gridSearch.fit(xTreino, yTreino)

classifier = gridSearch.best_estimator_

print('\nClassificador:', classifier.__class__)
print('\nScoring:', scoring)
print('Score:', score)
print('\nMelhor parametrização: %s' % gridSearch.best_params_)
print('Melhor pontuação: %.2f' % gridSearch.best_score_)

#K-fold
print('\n========== VALIDAÇÃO MÉTODO K-FOLD ==========')
arrayYReal = []
arrayYPrediction = []
arrayAcuracia = []
arrayConfusion = np.array([[0, 0], [0, 0]])
cv_iter = kfold.split(xTreino, yTreino)
for treino, teste in cv_iter:
    #Etapa de treinamento
    classifier.fit(xTreino[treino], yTreino[treino])
    
    #Etapa de predição
    yPrediction = classifier.predict(xTreino[teste])
    
    arrayYReal = np.append(arrayYReal, yTreino[teste])
    arrayYPrediction = np.append(arrayYPrediction, yPrediction)
    
    arrayConfusion += confusion_matrix(yTreino[teste], yPrediction, labels=[0, 1])
    arrayAcuracia.append(accuracy_score(yTreino[teste], yPrediction))

print(pd.DataFrame(arrayConfusion, index=['real:descartado', 'real:confirmado'], 
                   columns=['pred:descartado', 'pred:confirmado']))

print("\n(TN, FP, FN, TP): %s \n" % arrayConfusion.ravel())
print(classification_report(arrayYReal, arrayYPrediction, labels=[0, 1]))

#Validação 
print('\n========== TESTE ==========')
#Etapa de treinamento
classifier.fit(xTreino, yTreino)

#Etapa de predição
yPrediction = classifier.predict(xTeste)

cm = confusion_matrix(yTeste, yPrediction, labels=[0, 1])

print(pd.DataFrame(cm, index=['real:descartado', 'real:confirmado'], 
                   columns=['pred:descartado', 'pred:confirmado']))

print("\n(TN, FP, FN, TP): %s \n" % cm.ravel())

print(classification_report(yTeste, yPrediction, labels=[0, 1]))