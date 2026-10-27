/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f0xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */
#define FRAME_TIMEOUT 500
/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define MENU_BUTTON_Pin GPIO_PIN_0
#define MENU_BUTTON_GPIO_Port GPIOA
#define STATUS_RED_Pin GPIO_PIN_10
#define STATUS_RED_GPIO_Port GPIOB
#define STATUS_GREEN_Pin GPIO_PIN_11
#define STATUS_GREEN_GPIO_Port GPIOB
#define HEALTH_LED_1_Pin GPIO_PIN_3
#define HEALTH_LED_1_GPIO_Port GPIOB
#define HEALTH_LED_2_Pin GPIO_PIN_4
#define HEALTH_LED_2_GPIO_Port GPIOB
#define HEALTH_LED_3_Pin GPIO_PIN_5
#define HEALTH_LED_3_GPIO_Port GPIOB
#define HEALTH_LED_4_Pin GPIO_PIN_6
#define HEALTH_LED_4_GPIO_Port GPIOB
#define HEALTH_LED_5_Pin GPIO_PIN_7
#define HEALTH_LED_5_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
