# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 16:41:44 2024

@author: EParraga
"""
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import numpy as np

def prediction_lineal(summary, X_metric, x2_metric, y_metric, positions):
    #X = df[['Nodes', 'Processes']]
    linear_model = LinearRegression()
    linear_model.fit(summary[[x2_metric, X_metric]].values, summary[f'{y_metric}_mean'].values)

    #linear_model.fit(summary[[x2_metric,X_metric]].values.reshape(-1, 1), summary[f'{y_metric}_mean'].values)
    positions = summary[[x2_metric, X_metric]].values  # Asumiendo que tienes 'Nodes' en summary

    # Predicciones
   # y_pred_linear = linear_model.predict(positions.reshape(-1, 2))
    y_pred_linear = linear_model.predict(positions)  # Aquí, 'positions' debe ser de forma (n_samples, 2)

    # Error cuadrático medio
    mse_linear = mean_squared_error(summary[f'{y_metric}_mean'].values, y_pred_linear)
    print(f'MSE Lineal: {mse_linear}')
    
    # Calcular el margen de error
    margin_of_error = 1.96 * summary[f'{y_metric}_std'].mean()  # 95% de intervalo de confianza

    # Coeficientes del modelo lineal
    coef = linear_model.coef_
    intercept = linear_model.intercept_
    #print(f"Modelo lineal: IO_Time = {intercept:.4f} + {coef[0]:.4f} * Nodes + {coef[1]:.4f} * Processes")
    print(f"Modelo lineal: {y_metric} = {intercept:.4f} + {coef[0]:.4f} * {x2_metric} + {coef[1]:.4f} * {X_metric}")

    #print(f"Modelo lineal: {y_metric} = {intercept:.4f} + {coef[0]:.4f} * {X_metric}")
    return y_pred_linear, margin_of_error

def prediction_polinomial(summary, X_metric, x2_metric, y_metric, degree):
    # Generar características polinómicas
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(summary[[x2_metric, X_metric]].values)
    
    # Crear el modelo de regresión lineal (que será aplicado a las características polinómicas)
    poly_model = LinearRegression()
    poly_model.fit(X_poly, summary[f'{y_metric}_mean'].values)
    
    # Realizar las predicciones
    y_pred_poly = poly_model.predict(X_poly)
    
    # Error cuadrático medio
    mse_poly = mean_squared_error(summary[f'{y_metric}_mean'].values, y_pred_poly)
    print(f'MSE Polinómico (grado {degree}): {mse_poly}')
    
    # Calcular el margen de error
    margin_of_error = 1.96 * summary[f'{y_metric}_std'].mean()  # 95% de intervalo de confianza
    
    # Coeficientes del modelo polinómico
    coef = poly_model.coef_
    intercept = poly_model.intercept_
    print(f"Modelo polinómico (grado {degree}): {y_metric} = {intercept:.8f} + {' + '.join([f'{coef[i]:.8f} * x^{i}' for i in range(1, len(coef))])}")
    
    return y_pred_poly, margin_of_error
    
def prediction_polinomial1(summary, X_metric, y_metric, degree):
    # Generar características polinómicas
    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(summary[[X_metric]].values)
    
    # Crear el modelo de regresión lineal (que será aplicado a las características polinómicas)
    poly_model = LinearRegression()
    poly_model.fit(X_poly, summary[f'{y_metric}_mean'].values)
    
    # Realizar las predicciones
    y_pred_poly = poly_model.predict(X_poly)
    
    # Error cuadrático medio
    mse_poly = mean_squared_error(summary[f'{y_metric}_mean'].values, y_pred_poly)
    print(f'MSE Polinómico (grado {degree}): {mse_poly}')
    
    # Calcular el margen de error
    margin_of_error = 1.96 * summary[f'{y_metric}_std'].mean()  # 95% de intervalo de confianza
    
    # Coeficientes del modelo polinómico
    coef = poly_model.coef_
    intercept = poly_model.intercept_
    print(f"Modelo polinómico (grado {degree}): {y_metric} = {intercept:.8f} + {' + '.join([f'{coef[i]:.8f} * x^{i}' for i in range(1, len(coef))])}")
    
    return y_pred_poly, margin_of_error
