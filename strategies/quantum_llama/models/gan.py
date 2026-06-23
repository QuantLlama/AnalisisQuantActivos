import torch
import torch.nn as nn
import torch.optim as optim

class WGAN_GP:
    def __init__(self, generator, discriminator, config):
        self.generator = generator
        self.discriminator = discriminator
        self.config = config
        self.device = config.DEVICE
        
        self.g_optimizer = optim.Adam(self.generator.parameters(), lr=config.LEARNING_RATE_G, betas=(0.5, 0.9))
        self.d_optimizer = optim.Adam(self.discriminator.parameters(), lr=config.LEARNING_RATE_D, betas=(0.5, 0.9))
        
        self.generator.to(self.device)
        self.discriminator.to(self.device)

    def compute_gradient_penalty(self, real_samples, fake_samples):
        """Calculates the gradient penalty loss for WGAN GP"""
        alpha = torch.rand((real_samples.size(0), 1, 1)).to(self.device)
        interpolates = (alpha * real_samples + (1 - alpha) * fake_samples).requires_grad_(True)
        d_interpolates = self.discriminator(interpolates)
        fake = torch.ones((real_samples.size(0), 1)).to(self.device)
        
        gradients = torch.autograd.grad(
            outputs=d_interpolates,
            inputs=interpolates,
            grad_outputs=fake,
            create_graph=True,
            retain_graph=True,
            only_inputs=True,
        )[0]
        
        gradients = gradients.reshape(gradients.size(0), -1)
        gradient_penalty = ((gradients.norm(2, dim=1) - 1) ** 2).mean()
        return gradient_penalty

    def train_step(self, real_data):
        batch_size = real_data.size(0)
        real_data = real_data.to(self.device)
        
        # --- Train Discriminator ---
        for _ in range(self.config.CRITIC_ITERATIONS):
            self.d_optimizer.zero_grad()
            
            # Generate fake data
            # Noise input for generator? Or past sequence?
            # In time series forecasting, we usually use past sequence to predict future.
            # So "noise" is actually the input sequence X.
            # real_data here should be the target Y? Or X+Y?
            # Let's assume real_data is the full sequence.
            
            # For this implementation, let's assume we are generating the *next* step based on history.
            # But GANs usually generate from noise.
            # In conditional GANs for time series, we condition on history.
            
            # Simplified: Generator takes real_data (history) and outputs prediction.
            fake_data = self.generator(real_data) 
            
            real_validity = self.discriminator(real_data)
            fake_validity = self.discriminator(fake_data.detach())
            
            gradient_penalty = self.compute_gradient_penalty(real_data, fake_data.detach())
            
            d_loss = -torch.mean(real_validity) + torch.mean(fake_validity) + self.config.LAMBDA_GP * gradient_penalty
            d_loss.backward()
            self.d_optimizer.step()
            
        # --- Train Generator ---
        self.g_optimizer.zero_grad()
        fake_data = self.generator(real_data)
        fake_validity = self.discriminator(fake_data)
        
        g_loss = -torch.mean(fake_validity)
        
        # Add L1 Loss (MAE) to ensure prediction is close to ground truth (if available)
        # This makes it a hybrid GAN-LSTM
        # g_loss += nn.L1Loss()(fake_data, real_data) * 100
        
        g_loss.backward()
        self.g_optimizer.step()
        
        return d_loss.item(), g_loss.item()
