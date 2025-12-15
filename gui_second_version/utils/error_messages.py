"""User-friendly error message builder for common error scenarios."""

from __future__ import annotations


class ErrorMessageBuilder:
    """Build helpful, actionable error messages for users."""

    @staticmethod
    def network_error(ssid: str, details: str) -> str:
        """
        Build network connection error message.

        Args:
            ssid: The SSID that failed to connect
            details: Technical error details

        Returns:
            User-friendly error message with troubleshooting steps
        """
        return (
            f"Failed to connect to WiFi network '{ssid}'.\n\n"
            f"Details: {details}\n\n"
            f"Troubleshooting:\n"
            f"• Check that the password is correct\n"
            f"• Ensure the network is in range\n"
            f"• Try rescanning for networks\n"
            f"• Restart the WiFi adapter if problem persists\n"
            f"• Contact support if the issue continues"
        )

    @staticmethod
    def camera_error(camera_index: int, details: str) -> str:
        """
        Build camera error message.

        Args:
            camera_index: The camera index that failed
            details: Technical error details

        Returns:
            User-friendly error message with troubleshooting steps
        """
        return (
            f"Failed to access camera at index {camera_index}.\n\n"
            f"Details: {details}\n\n"
            f"Troubleshooting:\n"
            f"• Check that the camera is properly connected\n"
            f"• Try unplugging and reconnecting the camera\n"
            f"• Check USB cable and port\n"
            f"• Try a different USB port\n"
            f"• Verify camera permissions\n"
            f"• Restart the system if problem persists"
        )

    @staticmethod
    def process_error(
        process_name: str, exit_code: int, stderr: str, max_stderr_length: int = 500
    ) -> str:
        """
        Build process execution error message.

        Args:
            process_name: Name of the process that failed
            exit_code: Process exit code
            stderr: Standard error output from the process
            max_stderr_length: Maximum length of stderr to include

        Returns:
            User-friendly error message with error details
        """
        # Truncate stderr if too long
        stderr_display = stderr[:max_stderr_length]
        if len(stderr) > max_stderr_length:
            stderr_display += "\n[... truncated ...]"

        return (
            f"Process '{process_name}' failed with exit code {exit_code}.\n\n"
            f"Error output:\n{stderr_display}\n\n"
            f"This is a technical error. Please:\n"
            f"• Take a screenshot of this message\n"
            f"• Note what you were doing when the error occurred\n"
            f"• Contact support with this information"
        )

    @staticmethod
    def validation_error(field: str, value: str, expected: str) -> str:
        """
        Build validation error message.

        Args:
            field: Field name that failed validation
            value: The invalid value entered
            expected: Expected format/value description

        Returns:
            User-friendly validation error message
        """
        # Sanitize value for display (truncate if too long)
        display_value = value[:100]
        if len(value) > 100:
            display_value += "..."

        return (
            f"Invalid {field}: '{display_value}'\n\n"
            f"Expected format: {expected}\n\n"
            f"Please correct the input and try again."
        )

    @staticmethod
    def permission_error(resource: str, operation: str) -> str:
        """
        Build permission error message.

        Args:
            resource: The resource that couldn't be accessed
            operation: The operation that was attempted

        Returns:
            User-friendly permission error message
        """
        return (
            f"Permission denied when trying to {operation}:\n{resource}\n\n"
            f"This operation requires elevated privileges.\n\n"
            f"Troubleshooting:\n"
            f"• Ensure you have the necessary permissions\n"
            f"• You may need to enter your sudo password\n"
            f"• Check file/directory ownership and permissions\n"
            f"• Contact your system administrator if needed"
        )

    @staticmethod
    def file_not_found_error(filepath: str, context: str = "") -> str:
        """
        Build file not found error message.

        Args:
            filepath: The file that wasn't found
            context: Optional context about why the file is needed

        Returns:
            User-friendly file not found error message
        """
        message = f"Required file not found:\n{filepath}\n\n"

        if context:
            message += f"Context: {context}\n\n"

        message += (
            f"Troubleshooting:\n"
            f"• Check that the file exists at the specified location\n"
            f"• Verify the file path is correct\n"
            f"• Check file permissions\n"
            f"• The file may have been moved or deleted"
        )

        return message

    @staticmethod
    def configuration_error(config_key: str, issue: str) -> str:
        """
        Build configuration error message.

        Args:
            config_key: The configuration key with an issue
            issue: Description of the configuration issue

        Returns:
            User-friendly configuration error message
        """
        return (
            f"Configuration error for '{config_key}':\n{issue}\n\n"
            f"The application configuration may be invalid or corrupted.\n\n"
            f"Troubleshooting:\n"
            f"• Check the configuration file for errors\n"
            f"• Restore from backup if available\n"
            f"• Contact support for assistance"
        )

    @staticmethod
    def timeout_error(operation: str, timeout_seconds: int) -> str:
        """
        Build timeout error message.

        Args:
            operation: The operation that timed out
            timeout_seconds: How long we waited before timing out

        Returns:
            User-friendly timeout error message
        """
        return (
            f"Operation timed out: {operation}\n\n"
            f"Waited for {timeout_seconds} seconds before giving up.\n\n"
            f"Troubleshooting:\n"
            f"• The operation may need more time to complete\n"
            f"• Check system resources (CPU, memory, network)\n"
            f"• Try the operation again\n"
            f"• Contact support if the issue persists"
        )

    @staticmethod
    def service_error(service_name: str, action: str, details: str) -> str:
        """
        Build service management error message.

        Args:
            service_name: Name of the systemd service
            action: Action that failed (start, stop, restart, etc.)
            details: Technical error details

        Returns:
            User-friendly service error message
        """
        return (
            f"Failed to {action} service '{service_name}'.\n\n"
            f"Details: {details}\n\n"
            f"Troubleshooting:\n"
            f"• Check service configuration files\n"
            f"• View service logs: journalctl -u {service_name}\n"
            f"• Ensure service is properly installed\n"
            f"• Check for conflicting services\n"
            f"• Contact support with the error details above"
        )

    @staticmethod
    def dependency_error(dependency: str, required_by: str) -> str:
        """
        Build dependency error message.

        Args:
            dependency: The missing dependency
            required_by: What requires this dependency

        Returns:
            User-friendly dependency error message
        """
        return (
            f"Missing required dependency: {dependency}\n\n"
            f"Required by: {required_by}\n\n"
            f"This component is required for the system to function properly.\n\n"
            f"Troubleshooting:\n"
            f"• Run the installation script to install dependencies\n"
            f"• Check that all required packages are installed\n"
            f"• Contact support if the issue persists"
        )

    @staticmethod
    def hardware_error(hardware: str, issue: str) -> str:
        """
        Build hardware error message.

        Args:
            hardware: The hardware component with an issue
            issue: Description of the hardware issue

        Returns:
            User-friendly hardware error message
        """
        return (
            f"Hardware issue detected: {hardware}\n\n"
            f"Problem: {issue}\n\n"
            f"Troubleshooting:\n"
            f"• Check hardware connections\n"
            f"• Verify hardware is powered on\n"
            f"• Try reconnecting the hardware\n"
            f"• Check for hardware compatibility\n"
            f"• Contact support if hardware appears faulty"
        )

    @staticmethod
    def generic_error_with_recovery(error_msg: str, recovery_steps: list[str]) -> str:
        """
        Build a generic error message with custom recovery steps.

        Args:
            error_msg: The error message
            recovery_steps: List of recovery action strings

        Returns:
            User-friendly error message with recovery steps
        """
        message = f"{error_msg}\n\n"

        if recovery_steps:
            message += "Suggested actions:\n"
            for step in recovery_steps:
                message += f"• {step}\n"
        else:
            message += "Please try again or contact support."

        return message
