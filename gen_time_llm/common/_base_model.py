# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/common.base_model.ipynb.

# %% auto 0
__all__ = ['BaseModel']

# %% ../../nbs/common.base_model.ipynb 2
import numpy as np
import torch
import random
import torch.nn as nn
import pytorch_lightning as pl
from pytorch_lightning.callbacks.early_stopping import EarlyStopping

# %% ../../nbs/common.base_model.ipynb 3
class BaseModel(pl.LightningModule):
    """
    BaseModel for time series to text tasks.
    
    This base class is designed for models that take time series data as input and generate textual summaries.
    """

    def __init__(
        self,
        random_seed,
        loss,  # Loss function
        valid_loss=None,  # Validation loss (optional)
        optimizer=torch.optim.Adam,  # Default optimizer
        optimizer_kwargs=None,  # Additional arguments for optimizer
        lr_scheduler=torch.optim.lr_scheduler.StepLR,  # Default learning rate scheduler
        lr_scheduler_kwargs=None,  # Additional arguments for lr scheduler
        max_steps=10000,  # Max number of training steps
        early_stop_patience_steps=1000,  # Patience for early stopping
        output_key="summary_input_ids",  # Fixed output key for summary
        input_keys=None,  # Keys to extract from the batch (dynamically chosen by the model)
        **trainer_kwargs,
    ):
        super().__init__()
        self.save_hyperparameters()

        # Set random seed for reproducibility
        self.random_seed = random_seed
        pl.seed_everything(self.random_seed, workers=True)

        # Loss
        self.loss = loss
        self.valid_loss = valid_loss if valid_loss is not None else loss

        # Optimization
        self.optimizer = optimizer
        self.optimizer_kwargs = optimizer_kwargs if optimizer_kwargs is not None else {}

        # Learning rate scheduler
        self.lr_scheduler = lr_scheduler
        self.lr_scheduler_kwargs = lr_scheduler_kwargs if lr_scheduler_kwargs is not None else {}

        # Input and output keys
        self.output_key = output_key  # Summary key (fixed)
        self.input_keys = input_keys if input_keys is not None else []  # Dynamic input keys

        # Trainer configuration
        self.max_steps = max_steps
        self.early_stop_patience_steps = early_stop_patience_steps
        self.trainer_kwargs = trainer_kwargs

        # Add early stopping
        if early_stop_patience_steps > 0:
            if "callbacks" not in trainer_kwargs:
                trainer_kwargs["callbacks"] = []
            trainer_kwargs["callbacks"].append(
                EarlyStopping(monitor="val_loss", patience=early_stop_patience_steps)
            )

    def forward(self, batch):
        """
        Forward pass of the model.
        Models should implement their custom forward logic using the `input_keys` to select specific inputs from the batch.
        """
        # Extract inputs based on specified keys
        inputs = {key: batch[key] for key in self.input_keys}
        # Models will implement their forward pass logic using these inputs
        raise NotImplementedError("Subclasses must implement the forward method.")

    def training_step(self, batch, batch_idx):
        """
        Training step: compute loss for a single batch.
        """
        target = batch[self.output_key]

        # Decide whether to use teacher forcing based on a random threshold
        use_teacher_forcing = torch.rand(1).item() < 0.8

        if use_teacher_forcing:
            # Teacher forcing: GPT computes the loss internally
            loss = self(batch, targets=target, use_teacher_forcing=True)
        else:
            # Autoregressive generation: no loss from GPT, so we compute it manually
            output = self(batch, use_teacher_forcing=False)
            
            # Use the target's length to trim or adjust the output
            # Target has shape (batch_size, target_length)
            # Compare the generated output tokens (output) with the target token IDs
            target = target[:, 1:]  # Shift target to ignore the first token (as autoregressive generation predicts next tokens)

            output = output[:, :target.size(1), :]  # Trim output to match target length
            
            # Reshape output and target for CrossEntropyLoss
            output = output.reshape(-1, output.size(-1))
            target = target.reshape(-1)

            # Compute the loss manually
            loss = self.loss(output, target)

        # Log the loss
        self.log("train_loss", loss, prog_bar=True)

        return loss

    def validation_step(self, batch, batch_idx):
        """
        Validation step: compute validation loss for a single batch.
        """
        target = batch[self.output_key]

        # In validation, we typically don't use teacher forcing, so we just run autoregressive generation
        output = self(batch, use_teacher_forcing=False)

        # Use the target's length to trim or adjust the output
        # Target has shape (batch_size, target_length)
        # Compare the generated output tokens (output) with the target token IDs
        target = target[:, 1:]  # Shift target to ignore the first token (as autoregressive generation predicts next tokens)

        output = output[:, :target.size(1), :]  # Trim output to match target length
        
        # Reshape output and target for CrossEntropyLoss
        output = output.reshape(-1, output.size(-1))
        target = target.reshape(-1)

        # Compute validation loss manually
        val_loss = self.valid_loss(output, target)

        # Log the validation loss
        self.log("val_loss", val_loss, prog_bar=True)

        return val_loss



    def configure_optimizers(self):
        """
        Configure the optimizer and learning rate scheduler.
        """
        optimizer = self.optimizer(params=self.parameters(), **self.optimizer_kwargs)

        lr_scheduler = {
            "scheduler": self.lr_scheduler(optimizer=optimizer, **self.lr_scheduler_kwargs),
            "monitor": "val_loss",  # Monitor validation loss
            "interval": "step",  # Step-based scheduler
        }
        return {"optimizer": optimizer, "lr_scheduler": lr_scheduler}

    def __repr__(self):
        return type(self).__name__

    def _restart_seed(self, random_seed):
        """
        Helper method to restart the random seed.
        """
        if random_seed is None:
            random_seed = self.random_seed
        torch.manual_seed(random_seed)

    def on_fit_start(self):
        """
        Method called at the start of training to set random seeds.
        """
        torch.manual_seed(self.random_seed)
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)

