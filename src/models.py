"""
Pydantic models for data validation across the application.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import re


class LeadModel(BaseModel):
    """Model for validating lead data before saving to NocoDB."""
    
    nome: str = Field(..., min_length=3, max_length=100)
    cpf: str = Field(..., description="CPF in format XXX.XXX.XXX-XX")
    telefone: str = Field(..., description="Phone in format (XX) XXXXX-XXXX")
    modelo_interesse: str = Field(..., min_length=1, max_length=100)
    nascimento: str = Field(..., description="Birth date in format DD/MM/YYYY")
    cnh: Literal["SIM", "NÃO"] = Field(..., description="Has driver's license")
    
    @field_validator("nome")
    @classmethod
    def validate_nome(cls, v):
        """Validate and trim name."""
        v = v.strip()
        if not v or not re.match(r"^[a-zA-ZÀ-ÿ\s]+$", v):
            raise ValueError("Nome deve conter apenas letras e espaços")
        return v
    
    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v):
        """Validate CPF format and basic checksum."""
        # Remove common formatting
        cpf_clean = re.sub(r"\D", "", v)
        
        if len(cpf_clean) != 11:
            raise ValueError("CPF deve conter 11 dígitos")
        
        # Basic validation: all same digit is invalid
        if len(set(cpf_clean)) == 1:
            raise ValueError("CPF inválido")
        
        # Format to XXX.XXX.XXX-XX for storage
        formatted_cpf = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"
        return formatted_cpf
    
    @field_validator("telefone")
    @classmethod
    def validate_telefone(cls, v):
        """Validate phone format."""
        # Remove common formatting
        phone_clean = re.sub(r"\D", "", v)
        
        if len(phone_clean) < 10 or len(phone_clean) > 11:
            raise ValueError("Telefone deve conter 10 ou 11 dígitos")
        
        # Format to (XX) XXXXX-XXXX
        if len(phone_clean) == 11:
            formatted_phone = f"({phone_clean[:2]}) {phone_clean[2:7]}-{phone_clean[7:]}"
        else:
            formatted_phone = f"({phone_clean[:2]}) {phone_clean[2:6]}-{phone_clean[6:]}"
        
        return formatted_phone
    
    @field_validator("nascimento")
    @classmethod
    def validate_nascimento(cls, v):
        """Validate birth date format (DD/MM/YYYY)."""
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Data de nascimento deve estar no formato DD/MM/YYYY")
        return v
    
    @field_validator("modelo_interesse")
    @classmethod
    def validate_modelo(cls, v):
        """Trim and validate modelo."""
        v = v.strip()
        if not v:
            raise ValueError("Modelo de interesse é obrigatório")
        return v
    
    class Config:
        str_strip_whitespace = True


class WebhookMessage(BaseModel):
    """Model for validating incoming Instagram webhook payload."""
    
    sender_id: str = Field(..., description="Instagram user ID")
    text: str = Field(..., min_length=1, description="Message text")
    
    @field_validator("sender_id")
    @classmethod
    def validate_sender_id(cls, v):
        """Validate sender ID is numeric."""
        if not v.isdigit():
            raise ValueError("Sender ID must be numeric")
        return v
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        """Trim and validate message text."""
        v = v.strip()
        if not v:
            raise ValueError("Message text cannot be empty")
        return v
