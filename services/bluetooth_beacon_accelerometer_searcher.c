// Copyright (c) 2021 David G. Young
// Copyright (c) 2015 Damian Kołakowski. All rights reserved.
// Modified for FLASH-TV project

// Build with: cc bluetooth_beacon_accelerometer_searcher.c -lbluetooth -o bluetooth_beacon_accelerometer_searcher

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>

// Configuration
#define DEFAULT_TIMEOUT 30
#define MAX_DEVICES 100
#define BEACON_PATTERN_LENGTH 13
#define HCI_DEV_ID_PRIMARY 1
#define HCI_DEV_ID_FALLBACK 0

// Global variables
static int device_handle = -1;
static volatile sig_atomic_t keep_running = 1;
static char found_macs[MAX_DEVICES][18]; // Array to store found MAC addresses
static int found_count = 0;

/**
 * Structure for a BLE HCI request
 */
struct hci_request ble_hci_request(uint16_t ocf, int clen, void *status, void *cparam)
{
    struct hci_request rq = {0};
    rq.ogf = OGF_LE_CTL;
    rq.ocf = ocf;
    rq.cparam = cparam;
    rq.clen = clen;
    rq.rparam = status;
    rq.rlen = 1;
    return rq;
}

/**
 * Clean up resources and exit
 */
void cleanup_and_exit(int exit_code)
{
    int ret, status;

    if (device_handle < 0)
    {
        exit(exit_code);
    }

    // Disable scanning
    le_set_scan_enable_cp scan_cp = {0};
    scan_cp.enable = 0x00; // Disable flag

    struct hci_request disable_adv_rq = ble_hci_request(
        OCF_LE_SET_SCAN_ENABLE,
        LE_SET_SCAN_ENABLE_CP_SIZE,
        &status,
        &scan_cp);

    ret = hci_send_req(device_handle, &disable_adv_rq, 1000);
    if (ret < 0)
    {
        fprintf(stderr, "Failed to disable BLE scan: %s\n", strerror(errno));
    }

    hci_close_dev(device_handle);

    // Print all discovered devices before exiting
    for (int i = 0; i < found_count; i++)
    {
        printf("%s\n", found_macs[i]);
    }

    exit(exit_code);
}

/**
 * Handle signals (SIGINT, SIGTERM, SIGALRM)
 */
void signal_handler(int sig)
{
    switch (sig)
    {
    case SIGALRM:
        // Normal scan timeout - not an error
        break;
    case SIGINT:
    case SIGTERM:
        fprintf(stderr, "Received termination signal\n");
        break;
    }
    keep_running = 0;
}

/**
 * Add a MAC address to the found list if it's not already there
 */
void add_mac_address(const char *mac)
{
    // Check if this MAC is already in our list
    for (int i = 0; i < found_count; i++)
    {
        if (strcmp(found_macs[i], mac) == 0)
        {
            return; // Already found, don't add again
        }
    }

    // Add new MAC if we have space
    if (found_count < MAX_DEVICES)
    {
        strncpy(found_macs[found_count], mac, 18);
        found_macs[found_count][17] = '\0'; // Ensure null termination
        found_count++;
    }
}

/**
 * Check if the advertisement matches the expected pattern for our beacons
 */
bool is_valid_beacon_advertisement(const le_advertising_info *info)
{
    // Check minimum length
    if (info->length < BEACON_PATTERN_LENGTH)
    {
        return false;
    }

    // Check for the expected pattern
    // Format: 02 01 06 03 03 AA FE 10 16 AA FE 21 00
    const uint8_t expected_pattern[] = {
        0x02, 0x01, 0x06, 0x03, 0x03, 0xAA, 0xFE,
        0x10, 0x16, 0xAA, 0xFE, 0x21, 0x00};

    for (int i = 0; i < BEACON_PATTERN_LENGTH; i++)
    {
        if (info->data[i] != expected_pattern[i])
        {
            return false;
        }
    }

    return true;
}

/**
 * Initialize Bluetooth scanning
 */
bool initialize_bluetooth_scan()
{
    int status;
    int ret;

    // Try to open HCI device 1 first, then fallback to device 0
    device_handle = hci_open_dev(HCI_DEV_ID_PRIMARY);
    if (device_handle < 0)
    {
        device_handle = hci_open_dev(HCI_DEV_ID_FALLBACK);
        if (device_handle >= 0)
        {
            fprintf(stderr, "Using HCI device %d\n", HCI_DEV_ID_FALLBACK);
        }
    }
    else
    {
        fprintf(stderr, "Using HCI device %d\n", HCI_DEV_ID_PRIMARY);
    }

    if (device_handle < 0)
    {
        fprintf(stderr, "Failed to open HCI device: %s\n", strerror(errno));
        return false;
    }

    // Set BLE scan parameters
    le_set_scan_parameters_cp scan_params = {0};
    scan_params.type = 0x00;              // Passive scanning
    scan_params.interval = htobs(0x0010); // Scan interval
    scan_params.window = htobs(0x0010);   // Scan window
    scan_params.own_bdaddr_type = 0x00;   // Public device address
    scan_params.filter = 0x00;            // Accept all advertisements

    struct hci_request scan_params_req = ble_hci_request(
        OCF_LE_SET_SCAN_PARAMETERS,
        LE_SET_SCAN_PARAMETERS_CP_SIZE,
        &status,
        &scan_params);

    ret = hci_send_req(device_handle, &scan_params_req, 1000);
    if (ret < 0)
    {
        fprintf(stderr, "Failed to set scan parameters: %s\n", strerror(errno));
        return false;
    }

    // Set BLE events report mask
    le_set_event_mask_cp event_mask = {0};
    memset(event_mask.mask, 0xFF, sizeof(event_mask.mask));

    struct hci_request set_mask_req = ble_hci_request(
        OCF_LE_SET_EVENT_MASK,
        LE_SET_EVENT_MASK_CP_SIZE,
        &status,
        &event_mask);

    ret = hci_send_req(device_handle, &set_mask_req, 1000);
    if (ret < 0)
    {
        fprintf(stderr, "Failed to set event mask: %s\n", strerror(errno));
        return false;
    }

    // Enable scanning
    le_set_scan_enable_cp scan_cp = {0};
    scan_cp.enable = 0x01;     // Enable scanning
    scan_cp.filter_dup = 0x00; // Do not filter duplicates

    struct hci_request enable_scan_req = ble_hci_request(
        OCF_LE_SET_SCAN_ENABLE,
        LE_SET_SCAN_ENABLE_CP_SIZE,
        &status,
        &scan_cp);

    ret = hci_send_req(device_handle, &enable_scan_req, 1000);
    if (ret < 0)
    {
        fprintf(stderr, "Failed to enable scan: %s\n", strerror(errno));
        return false;
    }

    // Set up HCI filter
    struct hci_filter filter;
    hci_filter_clear(&filter);
    hci_filter_set_ptype(HCI_EVENT_PKT, &filter);
    hci_filter_set_event(EVT_LE_META_EVENT, &filter);

    if (setsockopt(device_handle, SOL_HCI, HCI_FILTER, &filter, sizeof(filter)) < 0)
    {
        fprintf(stderr, "Could not set socket options: %s\n", strerror(errno));
        return false;
    }

    return true;
}

/**
 * Main function
 */
int main()
{
    // Install signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGALRM, signal_handler);

    // Set timeout alarm
    alarm(DEFAULT_TIMEOUT);

    // Unblock signals
    sigset_t signal_set;
    sigemptyset(&signal_set);
    sigaddset(&signal_set, SIGALRM);
    sigaddset(&signal_set, SIGINT);
    sigaddset(&signal_set, SIGTERM);

    if (sigprocmask(SIG_UNBLOCK, &signal_set, NULL) != 0)
    {
        fprintf(stderr, "Could not unblock signals: %s\n", strerror(errno));
        return 1;
    }

    // Initialize Bluetooth scanning
    if (!initialize_bluetooth_scan())
    {
        return 1;
    }

    fprintf(stderr, "Scanning for Bluetooth beacons...\n");

    // Main scanning loop
    uint8_t buffer[HCI_MAX_EVENT_SIZE];
    int len;

    while (keep_running)
    {
        len = read(device_handle, buffer, sizeof(buffer));

        if (len < 0)
        {
            if (errno == EINTR)
            {
                // Interrupted by signal, check keep_running flag
                continue;
            }
            fprintf(stderr, "Error reading from HCI device: %s\n", strerror(errno));
            break;
        }

        if (len < HCI_EVENT_HDR_SIZE + 1)
        {
            continue;
        }

        // Process BLE advertisements
        evt_le_meta_event *meta_event = (evt_le_meta_event *)(buffer + HCI_EVENT_HDR_SIZE + 1);

        if (meta_event->subevent != EVT_LE_ADVERTISING_REPORT)
        {
            continue;
        }

        // Process advertisements
        uint8_t reports_count = meta_event->data[0];
        void *offset = meta_event->data + 1;

        while (reports_count--)
        {
            le_advertising_info *info = (le_advertising_info *)offset;

            // Convert Bluetooth address to string
            char addr[18];
            ba2str(&(info->bdaddr), addr);

            // Check if this device has the expected data format
            if (is_valid_beacon_advertisement(info))
            {
                add_mac_address(addr);
            }

            // Move to next advertisement in buffer
            offset = info->data + info->length + 2;
        }
    }

    // Clean up and exit
    cleanup_and_exit(0);
    return 0; // Never reached, but helps with static analysis
}