import torch

if __name__ == '__main__':
    cuda_available = torch.cuda.is_available()
    cuda_device = torch.cuda.current_device()

    if torch.cuda.is_available():
        print(f'Torch is using CUDA.{cuda_device} device ')
    else:
        print('Torch is not capable to use any of CUDA devices')

    number_of_cuda_devices = torch.cuda.device_count()

    print(f"Number of CUDA devices: {number_of_cuda_devices}")

    for i in range(number_of_cuda_devices):
        print(torch.cuda.get_device_name(i))
