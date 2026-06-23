import torch

class Config:
    # Data Settings
    DATA_PATH = 'data/futures_data.csv' # Placeholder path
    SEQ_LENGTH = 60 # Lookback period (e.g., 60 minutes or days)
    PREDICT_WINDOW = 1 # How many steps ahead to predict
    
    # Model Hyperparameters
    BATCH_SIZE = 64
    LEARNING_RATE_G = 0.001
    LEARNING_RATE_D = 0.0004
    LATENT_DIM = 100 # Dimension of random noise for GAN
    HIDDEN_DIM_LSTM = 128
    HIDDEN_DIM_CNN = 64
    NUM_LAYERS_LSTM = 2
    
    # Training Settings
    NUM_EPOCHS = 200
    CRITIC_ITERATIONS = 5 # Train discriminator n times per generator step
    LAMBDA_GP = 10 # Gradient penalty lambda
    
    # Device
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Features
    USE_FOURIER = True
    USE_SENTIMENT = True
    FOURIER_COMPONENTS = [3, 6, 9]

config = Config()
